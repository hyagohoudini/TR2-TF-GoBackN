import argparse
import RDT
import time


def upperCase(message):
    capitalizedSentence = message.upper()
    return capitalizedSentence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UPPER CASE server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    buffer = []

    timeout = 1000  # close connection if no new data within 5 seconds
    time_of_last_data = time.time()

    rdt = RDT.RDT('server', None, args.port)
    try:
        while True:
            msg_S = rdt.rdt_4_0_receive()
            
            if msg_S == []:
                if time_of_last_data + timeout < time.time():
                    break
                else:
                    continue
            time_of_last_data = time.time()


    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()
        print("Connection ended.")


