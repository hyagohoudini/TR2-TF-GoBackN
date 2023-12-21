import Network
import argparse
import time
from time import sleep
import hashlib

#debug = True    
debug = True

final_stat_corrupt_counter = 0
final_stat_chksum_corrupt_counter = 0
final_stat_data_sent_counter = 0
final_stat_resent_counter = 0
final_stat_ACK_resent_counter = 0
final_stat_total_bytes = 0
final_stat_useful_bytes = 0

def debug_log(message):
    if debug:
        print(message)


class Packet:
    # the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10
    # length of md5 checksum in hex
    checksum_length = 32

    header_length = seq_num_S_length + length_S_length + checksum_length

    def __init__(self, seq_num, msg_S):
        self.seq_num = seq_num
        self.msg_S = msg_S

    @classmethod
    def from_byte_S(self, byte_S):
        if Packet.corrupt(byte_S):
            raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')

        # extract the fields
        seq_num = int(byte_S[Packet.length_S_length: Packet.length_S_length + Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length + Packet.seq_num_S_length + Packet.checksum_length:]
        return self(seq_num, msg_S)

    def get_byte_S(self):
        # convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        # convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(
            self.length_S_length)
        # compute the checks0um
        checksum = hashlib.md5((length_S + seq_num_S + self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        # compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S

    @staticmethod
    def corrupt(byte_S):
        # extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length: Packet.seq_num_S_length + Packet.seq_num_S_length]
        checksum_S = byte_S[
                     Packet.seq_num_S_length + Packet.seq_num_S_length: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length:]

        # compute the checksum locally
        checksum = hashlib.md5(str(length_S + seq_num_S + msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        # and check if the same
        #if (checksum_S != computed_checksum_S):
        #    Packet.final_stat_corrupt_counter += 1
        #   return True
        #else:
        #    return False   
        
        return checksum_S != computed_checksum_S

    def is_ack_pack(self):
        if self.msg_S == '1' or self.msg_S == '0':
            return True
        return False


class RDT:
    # Sending
    base = 1
    next_seq_num = 1
    window_size = 4
    start_time = 0
    sndpkt = {}
    timeout = 3
    
    # Receiving
    expected_seq_num = 1
    byte_buffer = ''

    # Index of the last packet sent
    seq_num = 0

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)

    def disconnect(self):
        self.network.disconnect()

    def clearAttributes(self):
        self.base = 1
        self.next_seq_num = 1
        self.start_time = 0
        self.sndpkt = {}
        self.expected_seq_num = 1
        self.byte_buffer = ''
    
    def rdt_4_0_send(self, msg_list):
        global final_stat_data_sent_counter, final_stat_resent_counter, final_stat_total_bytes, final_stat_useful_bytes
        result = []
        for self.seq_num in range(len(msg_list)):
            
            if self.next_seq_num >= self.base + self.window_size:
                debug_log('SENDER: Window is full, waiting for response.')
                remaining = msg_list[self.seq_num:]
                break

            self.sndpkt[self.next_seq_num] = Packet(self.next_seq_num, msg_list[self.seq_num])

            debug_log(f'SENDER: Sending message {self.next_seq_num} :\n{self.sndpkt[self.next_seq_num].get_byte_S()}.')

            self.network.udt_send(self.sndpkt[self.next_seq_num].get_byte_S())
            final_stat_data_sent_counter += 1
            final_stat_total_bytes += len(self.sndpkt[self.next_seq_num].get_byte_S().encode('utf-8'))
            final_stat_useful_bytes += len(self.sndpkt[self.next_seq_num].get_byte_S().encode('utf-8')) - Packet.header_length

            if self.base == self.next_seq_num:
                debug_log('SENDER: Starting timer for base.')
                self.start_time = time.time()

            self.next_seq_num += 1

            if self.seq_num == len(msg_list) - 1:
                debug_log('SENDER: Last message sent.')
                remaining = []
                break

        
        while self.base <= self.next_seq_num:
            # wait for timeout or ack
            response = ''

            while response == '' and (self.start_time + self.timeout > time.time()):
                response = self.network.udt_receive()
                    
            #timeout
            if response == '':
                debug_log(f'SENDER: Timeout, resending packets. next_seq_num: {self.next_seq_num}, base: {self.base}.')
                self.start_time = time.time()
                limit = self.next_seq_num + 1 if self.next_seq_num == len(msg_list) else self.next_seq_num 
                for j in range(self.base, limit):
                    if j in self.sndpkt:
                        self.network.udt_send(self.sndpkt[j].get_byte_S())
                        final_stat_resent_counter += 1
                        final_stat_total_bytes += len(self.sndpkt[j].get_byte_S().encode('utf-8'))
                continue
            
            debug_log(f'SENDER: Received response:\n{response}.')

            self.byte_buffer = response
            
            while True:
                if len(self.byte_buffer) < Packet.length_S_length:
                    debug_log('SENDER: Not enough bytes to read packet length.')
                    break  # not enough bytes to read packet length
                # extract length of packet
                msg_length = int(self.byte_buffer[:Packet.length_S_length])
                if len(self.byte_buffer) < msg_length:
                    debug_log('SENDER: Not enough bytes to read the whole packet.')
                    break  # not enough bytes to read the whole packet
                
                debug_log(f'SENDER: Current Packet:\n{self.byte_buffer[:msg_length]}.')

                if Packet.corrupt(self.byte_buffer[:msg_length]):
                    global final_stat_chksum_corrupt_counter
                    debug_log('SENDER: Checksum failed, resending packets.')
                    final_stat_chksum_corrupt_counter += 1

                    #wait for timeout
                    while self.start_time + self.timeout > time.time():
                        pass
                    break

                response_p = Packet.from_byte_S(self.byte_buffer[:msg_length])

                # If the ACK is not for the base, ignore it
                if self.base != response_p.seq_num:
                    debug_log(f'SENDER: Received ACK {response_p.seq_num} but base is {self.base}.')
                    #wait for timeout
                    while self.start_time + self.timeout > time.time():
                        pass
                    break

                self.base = response_p.seq_num + 1  

                debug_log(f'SENDER: ACK {response_p.seq_num} received')
                
                debug_log('SENDER: Restarting timer.')
                self.start_time = time.time()

                # Append the content of the ACK in the result
                result.append((response_p.msg_S, self.start_time, final_stat_total_bytes))

                debug_log(f'SENDER: Incrementing base to {self.base}.')
                debug_log(f'SENDER: Next seq num is {self.next_seq_num}.')

                # Verify if there is space in the window
                if self.next_seq_num < self.base + self.window_size and len(remaining) > 0:
                    debug_log('SENDER: seq_num: {}, base: {}, next_seq_num: {}, window_size: {}'.format(self.seq_num, self.base, self.next_seq_num, self.window_size))
                    self.sndpkt[self.next_seq_num] = Packet(self.next_seq_num, msg_list[self.seq_num])
                    debug_log(f'SENDER: Window has space, sending message {self.next_seq_num} :\n{self.sndpkt[self.next_seq_num].get_byte_S()}.')
                    self.network.udt_send(self.sndpkt[self.next_seq_num].get_byte_S())
                    final_stat_data_sent_counter += 1
                    final_stat_total_bytes += len(self.sndpkt[self.next_seq_num].get_byte_S().encode('utf-8'))
                    final_stat_useful_bytes += len(self.sndpkt[self.next_seq_num].get_byte_S().encode('utf-8')) - Packet.header_length
                    
                    if self.next_seq_num == len(msg_list):
                        debug_log('SENDER: Last message sent.')
                        remaining = []
                    else:
                        self.seq_num += 1
                        self.next_seq_num += 1
                        remaining = msg_list[self.seq_num:]

                self.byte_buffer = self.byte_buffer[msg_length:]        

        return result
    

    def rdt_4_0_receive(self):
        global final_stat_data_sent_counter, final_stat_ACK_resent_counter, final_stat_total_bytes, final_stat_useful_bytes 
        ret_S = []
        
        byte_S = self.network.udt_receive()

        if byte_S == '':
            return ret_S
        
        debug_log(f'RECEIVER: Received message:\n{byte_S}.')

        self.byte_buffer = byte_S

        # Don't move on until seq_num has been toggled
        # keep extracting packets - if reordered, could get more than one
        while True:
            # check if we have received enough bytes
            if len(self.byte_buffer) < Packet.length_S_length:
                break  # not enough bytes to read packet length
            # extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                break  # not enough bytes to read the whole packet

            debug_log(f'RECEIVER: Current Packet:\n{self.byte_buffer[:length]}.')

            # Check if packet is corrupt
            if Packet.corrupt(self.byte_buffer[:length]):
                global final_stat_corrupt_counter
                debug_log(f'RECEIVER: Corrupt packet, ignoring the package.')
                final_stat_corrupt_counter += 1
            else:
                # create packet from buffer content
                p = Packet.from_byte_S(self.byte_buffer[0:length])
                content = p.msg_S.upper()
                if p.seq_num == self.expected_seq_num:
                    debug_log(f'RECEIVER: Received new. Send ACK {self.expected_seq_num} and increment expected_seq.')
                    # SEND ACK + DATA
                    answer = Packet(self.expected_seq_num, content)
                    self.network.udt_send(answer.get_byte_S())
                    final_stat_data_sent_counter += 1
                    debug_log("RECEIVER: Incrementing expected_seq from {} to {}".format(self.expected_seq_num, self.expected_seq_num + 1))
                    self.expected_seq_num += 1
                    ret_S.append(p.msg_S)
                # If the package is duplicated, resend the duplicate ACK
                elif p.seq_num < self.expected_seq_num:
                    debug_log(f'RECEIVER: Received duplicate. Resend ACK {p.seq_num}.')
                    answer = Packet(p.seq_num, content)
                    self.network.udt_send(answer.get_byte_S())
                    final_stat_ACK_resent_counter += 1
                # If the packet is not the expected one, resend the ACK
                else:
                    debug_log(f'RECEIVER: Received unexpected. Resend ACK {self.expected_seq_num - 1}.')
                    answer = Packet(self.expected_seq_num - 1, content)
                    self.network.udt_send(answer.get_byte_S())
                    final_stat_ACK_resent_counter += 1
                    
            # remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            
        return ret_S


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()

    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_3_0_send('MSG_FROM_CLIENT')
        sleep(2)
        print(rdt.rdt_3_0_receive())
        rdt.disconnect()


    else:
        sleep(1)
        print(rdt.rdt_3_0_receive())
        rdt.rdt_3_0_send('MSG_FROM_SERVER')
        rdt.disconnect()
        
