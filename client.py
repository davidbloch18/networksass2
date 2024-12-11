import socket
import api
import argparse
import api

# region Predefined

# The following are for convenience. You can use them to build expressions.
pi_c = api.NAMED_CONSTANTS.PI
tau_c = api.NAMED_CONSTANTS.TAU
e_c = api.NAMED_CONSTANTS.E

add_b = api.BINARY_OPERATORS.ADD
sub_b = api.BINARY_OPERATORS.SUB
mul_b = api.BINARY_OPERATORS.MUL
div_b = api.BINARY_OPERATORS.DIV
mod_b = api.BINARY_OPERATORS.MOD
pow_b = api.BINARY_OPERATORS.POW

neg_u = api.UNARY_OPERATORS.NEG
pos_u = api.UNARY_OPERATORS.POS

sin_f = api.FUNCTIONS.SIN
cos_f = api.FUNCTIONS.COS
tan_f = api.FUNCTIONS.TAN
sqrt_f = api.FUNCTIONS.SQRT
log_f = api.FUNCTIONS.LOG
max_f = api.FUNCTIONS.MAX
min_f = api.FUNCTIONS.MIN
pow_f = api.FUNCTIONS.POW
rand_f = api.FUNCTIONS.RAND

# endregion


def process_response(response: api.CalculatorHeader) -> None:
    if response.is_request:
        raise api.CalculatorClientError("Got a request instead of a response")
    if response.status_code == api.CalculatorHeader.STATUS_OK:
        result, steps = api.data_to_result(response)
        print("Result:", result)
        if steps:
            print("Steps:")
            expr, first, *rest = steps
            print(f"{expr} = {first}", end="\n" * (not bool(rest)))
            if rest:
                print("".join(map(lambda v: f"\n{' ' * len(expr)} = {v}", rest)))
    elif response.status_code == api.CalculatorHeader.STATUS_CLIENT_ERROR:
        err = api.data_to_error(response)
        raise api.CalculatorClientError(err)
    elif response.status_code == api.CalculatorHeader.STATUS_SERVER_ERROR:
        err = api.data_to_error(response)
        raise api.CalculatorServerError(err)
    else:
        raise api.CalculatorClientError(f"Unknown status code: {response.status_code}")


def client(
    server_address: tuple[str, int],
    expression: api.Expression,
    show_steps: bool = False,
    cache_result: bool = False,
    cache_control: int = api.CalculatorHeader.MAX_CACHE_CONTROL,
) -> None:
    server_prefix = f"{{{server_address[0]}:{server_address[1]}}}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(server_address)
        print(f"{server_prefix} Connection established")

        try:
            request_header = api.CalculatorHeader.from_expression(
                expression, show_steps, cache_result, cache_control
            )

            packed_request = request_header.pack()
            print(
                f"{server_prefix} Sending request of length {len(packed_request)} bytes"
            )
            client_socket.sendall(packed_request)

            response = client_socket.recv(api.BUFFER_SIZE)
            print(f"{server_prefix} Got response of length {len(response)} bytes")
            response_header = api.CalculatorHeader.unpack(response)
            process_response(response_header)

        except api.CalculatorError as e:
            print(f"{server_prefix} Got error: {str(e)}")
        except Exception as e:
            print(f"{server_prefix} Unexpected error: {str(e)}")
    print(f"{server_prefix} Connection closed")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="A Calculator Client.")

    arg_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=api.DEFAULT_SERVER_PORT,
        help="The port to connect to.",
    )
    arg_parser.add_argument(
        "-H",
        "--host",
        type=str,
        default=api.DEFAULT_SERVER_HOST,
        help="The host to connect to.",
    )
    arg_parser.add_argument(
        "-s",
        "--show-steps",
        action="store_true",
        help="Request the steps of the calculation.",
    )
    arg_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not cache the result of the calculation.",
    )
    arg_parser.add_argument(
        "--cache-control",
        type=int,
        default=2**16 - 1,
        help="The maximum age of the cached response that the client is willing to accept (in seconds).",
    )

    args = arg_parser.parse_args()

    host = args.host
    port = args.port
    show_steps = args.show_steps
    cache_result = not args.no_cache
    cache_control = args.cache_control

    # * Change in start (1)
    arg_parser.add_argument(
        "-e",
        "--expression",
        type=int,
        choices=range(1, 7),
        required=True,
        help="Choose an expression number (1-6).",
    )
    # Example expressions: (uncomment one of them for your needs)
    # (1) '(sin(max(2, 3 * 4, 5, 6 * ((7 * 8) / 9), 10 / 11)) / 12) * 13' = -0.38748277824137206
    if args.expression == 1:
        expr = mul_b(
            div_b(
                sin_f(
                    max_f(
                        2,
                        mul_b(3, 4),
                        5,
                        mul_b(6, div_b(mul_b(7, 8), 9)),
                        div_b(10, 11),
                    )
                ),
                12,
            ),
            13,
        )  # (1)

    # (2) '(max(2, 3) + 3)' = 6
    elif args.expression == 2:
        expr = add_b(max_f(2, 3), 3)  # (2)
    elif args.expression == 3:
        # (3) '3 + ((4 * 2) / ((1 - 5) ** (2 ** 3)))' = 3.0001220703125
        expr = add_b(3, div_b(mul_b(4, 2), pow_b(sub_b(1, 5), pow_b(2, 3))))  # (3)
    elif args.expression == 4:
        # (4) '((1 + 2) ** (3 * 4)) / (5 * 6)' = 17714.7
        expr = div_b(pow_b(add_b(1, 2), mul_b(3, 4)), mul_b(5, 6))  # (4)
    elif args.expression == 5:
        # (5) '-(-((1 + (2 + 3)) ** -(4 + 5)))' = 9.92290301275212e-08
        expr = neg_u(neg_u(pow_b(add_b(1, add_b(2, 3)), neg_u(add_b(4, 5)))))  # (5)
    elif args.expression == 6:
        # (6) 'max(2, (3 * 4), log(e), (6 * 7), (9 / 8))' = 42
        expr = max_f(2, mul_b(3, 4), log_f(e_c), mul_b(6, 7), div_b(9, 8))  # (6)
    # * Change in end (1)

    # Change the following values according to your needs:

    show_steps = True  # Request the steps of the calculation
    cache_result = True  # Request to cache the result of the calculation
    # If the result is cached, this is the maximum age of the cached response
    # that the client is willing to accept (in seconds)
    cache_control = 2**16 - 1

    # * Change in start (2)
    client((host, port), expr, show_steps, cache_result, cache_control)
    # * Change in end (2)
