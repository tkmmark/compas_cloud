# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from . import fd_pb2 as fd__pb2


class FdStub(object):
    """Missing associated documentation comment in .proto file"""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Reply = channel.unary_unary(
                '/compas_cloud.Fd/Reply',
                request_serializer=fd__pb2.FdRequest.SerializeToString,
                response_deserializer=fd__pb2.FdReply.FromString,
                )


class FdServicer(object):
    """Missing associated documentation comment in .proto file"""

    def Reply(self, request, context):
        """Missing associated documentation comment in .proto file"""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_FdServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Reply': grpc.unary_unary_rpc_method_handler(
                    servicer.Reply,
                    request_deserializer=fd__pb2.FdRequest.FromString,
                    response_serializer=fd__pb2.FdReply.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'compas_cloud.Fd', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Fd(object):
    """Missing associated documentation comment in .proto file"""

    @staticmethod
    def Reply(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/compas_cloud.Fd/Reply',
            fd__pb2.FdRequest.SerializeToString,
            fd__pb2.FdReply.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)