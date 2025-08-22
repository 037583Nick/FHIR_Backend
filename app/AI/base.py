from io import BytesIO
from PIL import Image
import base64
import numpy as np
import requests
import os
import trtis.api_pb2 as api_pb2
import trtis.grpc_service_pb2 as grpc_service_pb2
import trtis.grpc_service_pb2_grpc as grpc_service_pb2_grpc
import trtis.model_config_pb2 as model_config_pb2
import trtis.server_status_pb2 as server_status_pb2
import trtis.request_status_pb2 as request_status_pb2

# import .api_pb2 as api_pb2
# import .grpc_service_pb2 as grpc_service_pb2
# import .grpc_service_pb2_grpc as grpc_service_pb2_grpc
# import .model_config_pb2 as model_config_pb2
# import .server_status_pb2 as server_status_pb2
# import .request_status_pb2 as request_status_pb2
import grpc


def model_dtype_to_np(model_dtype):
    if model_dtype == model_config_pb2.TYPE_BOOL:
        return np.bool
    elif model_dtype == model_config_pb2.TYPE_INT8:
        return np.int8
    elif model_dtype == model_config_pb2.TYPE_INT16:
        return np.int16
    elif model_dtype == model_config_pb2.TYPE_INT32:
        return np.int32
    elif model_dtype == model_config_pb2.TYPE_INT64:
        return np.int64
    elif model_dtype == model_config_pb2.TYPE_UINT8:
        return np.uint8
    elif model_dtype == model_config_pb2.TYPE_UINT16:
        return np.uint16
    elif model_dtype == model_config_pb2.TYPE_FP16:
        return np.float16
    elif model_dtype == model_config_pb2.TYPE_FP32:
        return np.float32
    elif model_dtype == model_config_pb2.TYPE_FP64:
        return np.float64
    elif model_dtype == model_config_pb2.TYPE_STRING:
        return np.dtype(object)
    return None


class ModelNotReadyException(Exception):
    pass


class BasePreprocessor:
    # Initialize by calling load_image on the file name
    def __init__(self, fn, model_name, server=None, torch=False, model_ver="1.0"):
        self.fn = fn
        self.image = self.load_image(fn)
        self.model_name = model_name
        self.output_list = []
        self.torch = torch
        self.model_ver = model_ver
        
        # 從環境變數讀取 gRPC 伺服器地址，如果沒有則使用預設值
        if server is None:
            server = os.getenv("GRPC_SERVER_ADDRESS", "10.24.211.151:30121")
        self.server = server
        if not torch:
            MAX_MESSAGE_LENGTH = 4194304 * 32
            channel = grpc.insecure_channel(
                server,
                options=[
                    ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
                    ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
                ],
            )
            self.grpc_stub = grpc_service_pb2_grpc.GRPCServiceStub(channel)
            status_request = grpc_service_pb2.StatusRequest(model_name=model_name)
            self.model_response = self.grpc_stub.Status(status_request)
            if self.model_response.request_status.code != request_status_pb2.SUCCESS:
                raise Exception(self.model_response.request_status.msg)
            if (
                self.model_response.server_status.ready_state
                != server_status_pb2.SERVER_READY
            ):
                raise Exception("Server not ready.")
            if (
                list(
                    self.model_response.server_status.model_status[
                        model_name
                    ].version_status.values()
                )[-1].ready_state
                != server_status_pb2.MODEL_READY
            ):
                raise ModelNotReadyException("Model not ready.")

    # Return our saved image... Possibly used for debugging
    def get_image(self):
        return self.image

    def load_image(self, fn):
        # This function should load a file and return a numpy image
        raise NotImplementedError

    def preprocess_image(self):
        # The base class does not do any preprocess
        raise NotImplementedError

    def postprocess_image(self):
        raise NotImplementedError

    def infer_one(self, input_dataset):
        if self.torch:
            byte_io = BytesIO()
            np.save(byte_io, input_dataset)
            url = "http://{}/predictions/{}/{}/".format(self.server, self.model_name, self.model_ver)
            r = requests.post(url, data=byte_io.getvalue())
            return r.json()
        # Build bone age request
        output_dtype_list = []
        request = grpc_service_pb2.InferRequest()
        # Make sure our model name matches request
        model_name = list(self.model_response.server_status.model_status.keys())[0]
        request.model_name = model_name
        # Use the latest version
        request.model_version = -1
        # Input Headers
        for ins, data in zip(
            self.model_response.server_status.model_status[model_name].config.input,
            input_dataset,
        ):
            if -1 in ins.dims:
                request.meta_data.input.add(name=ins.name, dims=data.shape)
            else:
                request.meta_data.input.add(name=ins.name, dims=ins.dims)
            request.raw_input.extend([data.tobytes()])
        # Batch size 1
        request.meta_data.batch_size = 1
        # Output Headers
        for outs in self.model_response.server_status.model_status[
            model_name
        ].config.output:
            output_message = api_pb2.InferRequestHeader.Output()
            output_message.name = outs.name
            if outs.label_filename:
                # This is an output with classes
                output_message.cls.count = 1  # Number of classes to predict (ie. Top 5)
                output_dtype_list += [0]
            else:
                output_dtype_list += [model_dtype_to_np(outs.data_type)]
            request.meta_data.output.extend([output_message])  # add our output
        # Make Inference
        grpc_response = self.grpc_stub.Infer(request)
        output_list = []
        for i, outs in enumerate(grpc_response.meta_data.output):
            if outs.batch_classes:
                for batch in outs.batch_classes:
                    for clss in batch.cls:
                        output_list += [(clss.label, clss.value)]
            if outs.raw and type(output_dtype_list[i]) == type:
                output_list += [
                    np.frombuffer(
                        grpc_response.raw_output[i], dtype=output_dtype_list[i]
                    ).reshape(outs.raw.dims)
                ]
        self.output_list = output_list
        return output_list

    def get_output_list(self):
        return self.output_list

    def infer_many(self, input_dataset):
        # Todo: Merge infer_many with infer_one
        if self.torch:
            byte_io = BytesIO()
            np.save(byte_io, input_dataset)
            url = "http://{}/predictions/{}/{}/".format(self.server, self.model_name, self.model_ver)
            r = requests.post(url, data=byte_io.getvalue())
            return r.json()
        # Build bone age request
        output_dtype_list = []
        request = grpc_service_pb2.InferRequest()
        # Make sure our model name matches request
        model_name = list(self.model_response.server_status.model_status.keys())[0]
        request.model_name = model_name
        # Use the latest version
        request.model_version = -1
        # Batch size 1
        request.meta_data.batch_size = len(input_dataset)
        # Input Headers
        input_bytes = [[]] * len(
            self.model_response.server_status.model_status[model_name].config.input
        )
        for i, data in enumerate(input_dataset):
            for j, (ins, data2) in enumerate(
                zip(
                    self.model_response.server_status.model_status[
                        model_name
                    ].config.input,
                    data,
                )
            ):
                if i < 1:
                    if -1 in ins.dims:
                        request.meta_data.input.add(name=ins.name, dims=data2.shape)
                    else:
                        request.meta_data.input.add(name=ins.name, dims=ins.dims)
                if len(input_bytes[j]) == 0:
                    input_bytes[j] = data2.tobytes()
                else:
                    input_bytes[j] += data2.tobytes()
        request.raw_input.extend(input_bytes)

        # Output Headers
        for outs in self.model_response.server_status.model_status[
            model_name
        ].config.output:
            output_message = api_pb2.InferRequestHeader.Output()
            output_message.name = outs.name
            if outs.label_filename:
                # This is an output with classes
                output_message.cls.count = 1  # Number of classes to predict (ie. Top 5)
                output_dtype_list += [0]
            else:
                output_dtype_list += [model_dtype_to_np(outs.data_type)]
            request.meta_data.output.extend([output_message])  # add our output

        # Make Inference
        grpc_response = self.grpc_stub.Infer(request)
        output_list = []
        for i, outs in enumerate(grpc_response.meta_data.output):
            one_output = []
            if outs.batch_classes:
                for batch in outs.batch_classes:
                    for clss in batch.cls:
                        one_output += [(clss.label, clss.value)]
            if outs.raw and type(output_dtype_list[i]) == type:
                one_output += [
                    np.frombuffer(
                        grpc_response.raw_output[i], dtype=output_dtype_list[i]
                    ).reshape(outs.raw.dims)
                ]
            output_list += [one_output]
        self.output_list = output_list
        return output_list

    def get_results(self):
        raise NotImplementedError

    def npimg_to_base64(self, np_image):
        # Load image and generate a jpeg
        jpg_bytes = BytesIO()
        pil_img = Image.fromarray(np_image)
        pil_img.save(jpg_bytes, format="JPEG")
        jpg_bytes.seek(0)
        return base64.b64encode(jpg_bytes.getvalue()).decode()

    def npimg_to_base64_png(self, np_image):
        # Load image and generate a jpeg
        png_bytes = BytesIO()
        pil_img = Image.fromarray(np_image)
        pil_img.save(png_bytes, format="PNG")
        png_bytes.seek(0)
        return base64.b64encode(png_bytes.getvalue()).decode()

    def postprocess_text(self):
        raise NotImplementedError
