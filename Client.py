import argparse
import RDT
import time
import matplotlib.pyplot as plt

if __name__ == '__main__':
    final_stat_init_time = time.time()
    parser = argparse.ArgumentParser(description='Quotation client talking to a Pig Latin server.')
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    msg_L = [
        'The art of debugging is figuring out what you really told your program to do rather than what you thought you told it to do. -- Andrew Singer',
        'The good news about computers is that they do what you tell them to do. The bad news is that they do what you tell them to do. -- Ted Nelson',
        'It is hardware that makes a machine fast. It is software that makes a fast machine slow. -- Craig Bruce',
        'Before software should be reusable, it should be usable. -- Ralph Johnson',
        'The computer was born to solve problems that did not exist before. -- Bill Gates',
        'To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment. -- Ralph Waldo Emerson',
        'The only way to do great work is to love what you do. -- Steve Jobs',
        'Success is not final, failure is not fatal: It is the courage to continue that counts. -- Winston Churchill',
        'In three words I can sum up everything I\'ve learned about life: it goes on. -- Robert Frost',
        'The only limit to our realization of tomorrow will be our doubts of today. -- Franklin D. Roosevelt',
        'END_OF_MESSAGE'
    ]

    timeout = 1000  # send the next message if not response
    time_of_last_data = time.time()
    rdt = RDT.RDT('client', args.server, args.port)
    try:
            
        result = rdt.rdt_4_0_send(msg_L)
        final_stat_end_time = time.time()
        print(result)
        print('\n')
        x = []
        y1 = []
        y2 = []
        for i, msg_S in enumerate(result):
            time_of_msg = msg_S[1]-final_stat_init_time
            throughput = msg_S[2]/(time_of_msg)
            print('Client: Received the converted frase to: ' + msg_S[0] + '\nTime: ' + f'{time_of_msg:.4f}' + '\n')
            x.append(time_of_msg)
            y1.append(i+1)
            y2.append(throughput)


    except (KeyboardInterrupt, SystemExit):
        print("Ending connection...")
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        print("Ending connection...")
    finally:
        rdt.disconnect()

        print("Connection ended.")
        print("Qtde média de bytes por pacote: " + str(len(msg_L[2].encode('utf-8'))))
        print("Tempo de simulação: " + f"{(final_stat_end_time - final_stat_init_time):.2f}" + "s")
        # Truncar vazão e goodput para 2 casas decimais
        print(f"Vazão: {(RDT.final_stat_total_bytes)/(final_stat_end_time - final_stat_init_time):.2f} b/s")
        print(f"Goodput: {(RDT.final_stat_useful_bytes)/(final_stat_end_time - final_stat_init_time):.2f} b/s")
        print("Total de pacotes corrompidos: \n")
        print("\tCheckSums com erro: " + str(RDT.final_stat_chksum_corrupt_counter) + "\n")
        print("\tPacotes de dados: " + str(RDT.final_stat_corrupt_counter) + "\n")
        print("Total de pacotes retransmitidos: \n")
        print("\tDo tipo ACK: " + str(RDT.final_stat_ACK_resent_counter) + "\n")
        print("\tDe dados: " + str(RDT.final_stat_resent_counter) + "\n")
        print("Total de pacotes enviados: " + str(RDT.final_stat_data_sent_counter + RDT.final_stat_resent_counter + RDT.final_stat_ACK_resent_counter) + "\n")
        
        # plt.plot(x, y1)
        # plt.xlabel("Elapsed Time (s)")
        # plt.ylabel("Window's base")
        # plt.title("Reordenação: 20%")
        # plt.show()

        # New figure
        # plt.figure()
        
        # # New plot
        # plt.plot(x, y2)
        # plt.xlabel("Elapsed Time (s)")
        # plt.ylabel("Throughput (b/s)")
        # plt.show()