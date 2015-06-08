#!/usr/bin/python
__author__ = "Dell-Ray Sackett"
__version__ = "0.6"
import argparse

from PIL import Image
import numpy

from message import Message
from message import CryptoHelper


class Steganographer(object):
    """
    An object for performing Steganography on an image.
    """

    def __init__(self, **kwargs):
        """
        Initialize a Steganography object

        Keyword Arguments:
        inputFile -- The filename of the image you wish to embed information information.
        outputFile -- The filename of the image that will have your information in it.
        """

        self._input_file = ""
        self._output_file = ""
        self.__image_data = numpy.empty((1, 1, 1))
        self.__color_mode = ""
        self.__color_size = 0
        self.__image_size = (0, 0)
        self.__max_bits_storable = 0

        if kwargs:
            for arg in kwargs:
                if arg is "inputFile":
                    self._input_file = kwargs[arg]
                elif arg is "outputFile":
                    self._output_file = kwargs[arg]


    #Static Methods
    @staticmethod
    def int_to_bin_list(number):
        """
        Return the least significant 32 bits of a number as a list.

        Mandatory Arguments:
        number -- The number you would like returned as a list.
        """

        list_value = []
        for i in reversed(range(32)):
            """
            Iterate through the last 32 bits of the number passed. I single out
            each bit by bit shifting the number 1 (essentially a bit mask here)
            left by the current index then bitwise anding that against the
            original number. That gives me the value of that position then I
            shift it back by the index to make sure that the bit only occupies
            the 1 bit. If you don't do that last part then python with
            interpret it as whatever value that bit place holds. ie if it was
            the 8 bit and it was set then you will get 8 instead of 1.
            """
            list_value += [((1 << i) & number) >> i]
        return list_value

    @staticmethod
    def bin_list_to_int(bin_list):
        """
        Returns the integer value of a binary list.

        Mandatory Arguments:
        binList -- A list of 1s and 0s to be assembled back into an integer.
        """

        int_value = 0
        for i in range(32):
            """
            This is pretty simple. You just get the value from the current
            index. Which should only be a 1 or a 0. Then shift it left by the
            index. Lastly you add the number created by the shift to the
            current value.
            """
            int_value += bin_list[31 - i] << i
        return int_value

    @staticmethod
    def char_to_bin_list(char):
        """
        Return a list of 1s and 0s representing the binary of a character.

        Mandatory Arguments:
        char -- A character to be broken down into a list.
        """

        int_value = ord(char)
        list_value = []

        for i in reversed(range(8)):
            list_value += [((1 << i) & int_value) >> i]

        return list_value

    @staticmethod
    def bin_list_to_char(bin_list):
        """
        Take a binary List and turn it back into a char.

        Mandatory Arguments:
        binList -- A list of 1s and 0s to be back into a char.
        """
        int_value = 0

        for i in range(8):
            int_value += bin_list[7 - i] << i
        return chr(int_value)

    @staticmethod
    def message_to_bin_list(message):
        """
        Takes a message and turns it into a binary list

        Mandatory Arguments:
        message -- A string to be broken down into a list of binary values.
        """

        list_value = []
        for character in message:
            list_value += Steganographer.char_to_bin_list(character)
        return list_value

    @staticmethod
    def bin_list_to_message(bin_list):
        """
        This turns a binary list back into a message.

        Mandatory Arguments:
        binList -- A list of 1s and 0s to be converted back into a string.
            Must be divisible by 8.
        """

        if (len(bin_list) % 8) is not 0:
            raise ValueError("The input list is required to be evenly divisable by 8")

        list_tmp = []
        bit_counter = 0
        message = ""
        for value in range(0, len(bin_list)):
            list_tmp.append(bin_list[value])
            if bit_counter == 7:
                message += Steganographer.bin_list_to_char(list_tmp)
                list_tmp = []
                bit_counter = -1
            bit_counter += 1
        return message

    # I "Borrowed" this wholesale from stack exchange
    @staticmethod
    def set_bit(v, index, x):
        """
        Set the index:th bit of v to x, and return the new value.

        Mandatory Arguments:
        v -- A variable in which a bit is to be changed.
        index -- The index of the bit to change.
        x -- The value to change index in variable v to.
        """
        mask = 1 << index
        v &= ~mask
        if x:
            v |= mask
        return v

    @staticmethod
    def compare_pixels(image_a, image_b, pixels=512):
        """
        Compare the specified amount of pixel data of the two pictures given.
        """
        print("Reading " + str(pixels) + " pixels from " + image_a + " and " + image_b + ".")
        try:
            __oim = Image.open(image_a)
            __nim = Image.open(image_b)
        except IOError:
            print("Something went wrong trying to open the pictures")
            exit(1)

        __oimd = numpy.asarray(__oim)
        __nimd = numpy.asarray(__nim)

        if not (__nim.size[0] == __oim.size[0] and __nim.size[1] == __oim.size[1]):
            print("The images need to be the same size!")
            exit(1)

        __pixelIndex = 0
        try:
            for heightIndex in range(0, __oim.size[1]):
                for widthIndex in range(0, __oim.size[0]):
                    if __pixelIndex >= pixels:
                        raise Exception("Done!")
                    else:
                        print(str(__pixelIndex) + ": " +
                              str(__oimd[widthIndex][heightIndex]) + " --> " +
                              str(__nimd[widthIndex][heightIndex]))
                        __pixelIndex += 1
        except Exception:
            pass
        __oim.close()
        __nim.close()

    @staticmethod
    def read_message_from_file(filename):
        """
        Return the contents of a file as a string.

        Mandatory Arguments:
        filename - The filename to read the message from.
        """

        try:
            # This might not be a great idea but we are going to try to read the entire file into a string all at once.
            fd = open(filename, 'r')
            message = fd.read()
            fd.close()
        except IOError as e:
            raise e
        return message

    @staticmethod
    def write_message_to_file(message, filename):
        """
        Write a message, as a string, to a file.

        Mandatory Arguments:
        message - The string to be written to the file.
        filename - The name of the file to write the string to.
        """

        try:
            fd = open(filename, "w")
            fd.write(message)
            fd.close()
        except Exception as e:
            raise e

    # Instance Methods
    def initialize_image_data(self):
        """
        This prepares the class for image manipulation.
        """
        if self._input_file == "":
            raise ValueError("You must supply an input file name to encode "
                             + "decode, or compare pixels.")
        try:
            __imageIn = Image.open(self._input_file)
        except IOError as e:
            raise e
        
        # Without the numpy.copy() the data would be read only
        self.__image_data = numpy.copy(numpy.asarray(__imageIn))
        self.__color_mode = __imageIn.mode
        self.__image_size = __imageIn.size
        __imageIn.close()

        # Set color size
        if self.__color_mode == "RGB":
            self.__color_size = 3
        elif self.__color_mode == "RGBA":
            # Don't encode to the alpha value
            self.__color_size = 3
        elif self.__color_mode == "CMYK":
            self.__color_size = 4
        elif self.__color_mode == "YCbCr":
            self.__color_size = 4
        else:
            raise ValueError("The input image " + self._input_file +
                             " contains an unsupported color model.")

        # Calculate the maximum number of bits we'll be able to store.
        self.__max_bits_storable = self.__image_size[0] * self.__image_size[1]
        self.__max_bits_storable *= self.__color_size

    def save_output_image(self):
        """Save the stored image data to file"""

        __imageOut = Image.fromarray(self.__image_data)
        try:
            __imageOut.save(self._output_file, 'PNG', compress_level=0)
        except IOError as e:
            raise e
        except Exception as e:
            raise Exception("The encoding function encountered the following "
                            + "unhandled exception while attempting to save "
                            + "the image.\n" + str(e))
        # Close the image. I don't know if this is explicitly necessary but feels right. Ya know?
        __imageOut.close()

        # Sing songs of our success
        print("Image encode and saved as " + self._output_file)

    def encode_image(self, message):
        """
        Encode a message into a picture.
        """

        __message = message
        # Error Handling
        if self._output_file == "":
            raise ValueError("No output filename specified. Please specify"
                             + " a filename and call encode_image() again.")
        if self.__image_data.shape == (1, 1, 1):
            """Uninitialized image or smallest image ever."""
            try:
                self.initialize_image_data()
            except Exception as e:
                raise e
        if __message == "":
            raise ValueError("Message not set. Please set message and"
                             + " call encode_image() again.")

        __bit_sequence = Steganographer.int_to_bin_list(len(__message))
        __bit_sequence += Steganographer.message_to_bin_list(__message)

        # Pad the message
        __padSize = self.__color_size - (len(__bit_sequence) % self.__color_size)
        for i in range(0, __padSize):
            __bit_sequence += [0]

        if len(__bit_sequence) >= self.__max_bits_storable:
            raise ValueError("The message or message file provided was too "
                             + "to be encoded onto image " + self._input_file
                             + ".")

        """
        I am pretty sure this formatting is more levels than I can count
        against PEP8. I am going to leave it like this though because I think
        it is easier to read. I feel like Clark, Johnny, and Joe would likely
        agree.
        """
        __bitIndex = 0
        __bitList = [0, 0, 0]
        try:
            for heightIndex in range(0, self.__image_size[0]):

                for widthIndex in range(0, self.__image_size[1]):

                    for colorIndex in range(0, self.__color_size):

                        if __bitIndex >= len(__bit_sequence):
                            raise Exception("Done!")
                        else:
                            __bitList[colorIndex] = Steganographer.set_bit(
                                self.__image_data[widthIndex][heightIndex][colorIndex],
                                0,
                                __bit_sequence[__bitIndex])
                            __bitIndex += 1

                    self.__image_data[widthIndex][heightIndex] = __bitList
                    __bitList = [0, 0, 0]
        except Exception:
            pass
        try:
            self.save_output_image()
        except IOError as e:
            raise e

    def decode_image(self):

        if self.__image_data.shape == (1, 1, 1):
            try:
                self.initialize_image_data()
            except IOError as e:
                raise e

        #create a list to get the number of bits in the message
        __len_list = []

        #This shit...
        #There are 32 bits (Integer presumably, Python is a little willy-nilly
        # on primitive types) of length data at the beginning of the encoding
        # 32/3 = 10 with 2 bits left over. So I need the first 10 pixels worth
        # of LSBs and the Red and Green LSB out of the 11th pixel. So, I
        # iterate through all 11 and on the 11th pixel I store normally until
        # I hit the Blue value, then I just pass which ends both loops.
        try:
            __bit_index = 0
            for heightIndex in range(0, self.__image_size[0]):
                for widthIndex in range(0, self.__image_size[1]):
                    for colorIndex in range(0, self.__color_size):
                        if __bit_index >= 32:
                            raise Exception("Done!")
                        else:
                            __len_list.append(self.__image_data[widthIndex][heightIndex][colorIndex] & 1)
                            __bit_index += 1
        except Exception as e:
            pass
        #Now we know how many bits to expect so we convert that back into an Int and store it for later
        __message_length = Steganographer.bin_list_to_int(__len_list)

        #I found it was easier on me to just store the entire with the length data at first.
        # Also, to make the encoding loop easier I padded the end of it so it would be evenly
        # divisible by the number of colors in the image. Here I will just grab everything
        # out of the picture all at once and store it in total list. Then I will use the message
        # length information to iterate through only the message bits so I don't have to do any
        # silly shit in the inner for loop here to weed out the length/padding data.
        __total_list = []

        #I stored the message length in characters which are 8 bits a piece. However, I work mostly
        # in number of bits instead of bytes so I
        # have to convert it off of the bat.
        __message_bit_length = __message_length * 8

        #Iterate through all of the bits that I believe were encoded onto the image.
        try:
            __bits_processed = 0
            for heightIndex in range(0, self.__image_size[0]):

                for widthIndex in range(0, self.__image_size[1]):

                    for colorIndex in range(0, self.__color_size):

                        if __bits_processed >= (__message_bit_length + 32):
                            raise Exception("Done!")
                        else:
                            __total_list.append(
                                self.__image_data[widthIndex][heightIndex][colorIndex] & 1)
                            __bits_processed += 1

        except Exception as e:
            pass

        #create a list to store the message bit sequence
        __message_list = []

        print(len(__total_list))
        #Iterate from the end to the end of the message data. So the message will always start
        # at the 33nd (decimal value 32) bit because the length data is 32 bits long. Then if the
        # message is x long we want to count from 32 to x + 32 since the message data will essentially
        # be offset in the picture by 32 bits. This also leaves out the padding data because we are
        # only iterating to the end of the message data exactly so the padding will be left out of the
        # message. That is good because the bitStringToMessage function will return and error string
        # if the message data isn't cleanly divisible by 8. Which it wouldn't be with the padding.
        for index in range(32, __message_bit_length + 32):
            __message_list.append(__total_list[index])

        #Convert the message from a list of binary values do a string
        __message = Steganographer.bin_list_to_message(__message_list)

        return __message

    def encode_image_from_file(self, filename):
        """
        This function will open a file, read the contents, then pass the
        contents as a message to encode_image.

        Manditory Arguments:
        filename - The name of the file containing the message.
        """

        try:
            __message = Steganographer.read_message_from_file(filename)
        except IOError:
            print("The file " + filename + " could not be read.")
            return

        self.encode_image(__message)

    def decode_image_to_file(self, filename):
        """
        This function will decode the message in an image and dump the
        message into a file.

        Mandatory Arguments:
        filename - The name of the file to save the message to.
        """

        __message = self.decode_image()
        try:
            Steganographer.write_message_to_file(__message, filename)
        except IOError:
            print("There was a problem opening the file " + filename
                  + ".")
            return
        print("Message saved to " + filename + ".")


class EncryptedSteganographer(Steganographer):
    """
    This subclass of the Steganographer class adds encryption to the message.
    It requires that the intended recipient's public key and the sender's RSA
    key pair be provided. It will then generate a symmetric key to encrypt the
    actual message data with. The symmetric key, the sender's public key, a
    signature of the message, and the encrypted message with CBC IV attached
    will be encoded into the picture. It is likewise able to decode and
    decrypt messages embedded in a picture. To do so it requires the
    recipient's RSA key pair.
    """

    def __init__(self, **kwargs):
        """
        Initialize an EncryptedSteganographer object

        Keyword Arguments:
        inputFile -- The filename of the image you wish to embed
            information in.
        outputFile -- The filename of the image that will have your
            information in it.
        recipientPublicKeyFileName -- The file name of the recipient's public
            key.
        sendersKeyPairFileName -- The file name of the sender's RSA key pair.
        passphrase -- The passphrase for the senders key pair. Unprotected
            key pairs will not be supported.
        """

        try:
            self._recipient_public_key_filename = kwargs.pop("recipientPublicKeyFileName")
        except KeyError:
            raise KeyError("The recipientPublicKeyFileName argument is required " +
                "to initialize an EncryptedSteganographer.")
        try:
            self._senders_key_pair_filename = kwargs.pop("sendersKeyPairFileName")
            self._passphrase = kwargs.pop("passphrase")
        except KeyError:
            raise KeyError("The passphrase and sendersKeyPairFileName arguments " +
                "are required to initialize an EncryptedSteganographer")
        super(EncryptedSteganographer, self).__init__(**kwargs)

    def encrypt_and_encode_message(self, message):
        """
        This function will encrypt a message and encode it onto an image.
        """

        __message = CryptoHelper.encryptMessage(message,
                                                self._recipient_public_key_filename,
                                                self._senders_key_pair_filename,
                                                self._passphrase).dumpMessage()

        self.encode_image(__message)

    def encrypt_and_encode_message_from_file(self, message_file):
        """
        This function will encrypt a message and encode it onto an image.
        """

        try:
            __message = Steganographer.read_message_from_file(message_file)
        except IOError as e:
            raise e
        __message = CryptoHelper.encryptMessage(__message,
                                                self._recipient_public_key_filename,
                                                self._senders_key_pair_filename,
                                                self._passphrase).dumpMessage()
        self.encode_image(__message)

    def decrypt_and_decode_message(self):
        """
        This Method will decode an image with a message in it and then,
        decrypt that message.
        """

        __message = ""
        try:
            __message = self.decode_image()
        except Exception as e:
            print(e)
        __message = CryptoHelper.decryptMessage(
            Message.loadMessage(__message), self._senders_key_pair_filename,
            self._passphrase)

        return __message

    def decrypt_and_decode_message_to_file(self, message_file):
        """
        This Method will decode an image with a message in it and then,
        decrypt that message.
        """

        __message = ""
        try:
            __message = self.decode_image()
        except Exception as e:
            raise e
        __message = CryptoHelper.decryptMessage(
            Message.loadMessage(__message), self._senders_key_pair_filename,
            self._passphrase)
        try:
            Steganographer.write_message_to_file(__message, message_file)
        except IOError as e:
            raise e

if __name__ == "__main__":

    description_string = "This program will embed a message into an image."
    description_string += " It will also encrypt the message when called"
    description_string += " with the appropriate arguments."
    epilog_string = "Thank you for using steganographer!"


    #If we are being executed independently then parse the necessary arguments.
    parser = argparse.ArgumentParser(description=description_string,
                                     epilog=epilog_string)
    parser.add_argument("--inputimage","-ii",
                        help="The to encode the message onto or the encoded" +
                        " image if decoding.")
    parser.add_argument("--outputimage", "-oi",
                        help="The name of the encoded image.")
    parser.add_argument("--encode", "-e", action="store_true",
                        help="Encode a message onto a picture.")
    parser.add_argument("--decode", "-d", action="store_true",
                        help="Decode the input image and write message to" +
                        " terminal.")
    parser.add_argument("--crypto", action="store_true",
                        help="Use ciphered steganographer instead plaintext")


    parser.add_argument("--message", "-m",
                        help="The message to be encoded onto the picture.")
    parser.add_argument("--inputfile", "-if", help="--inputfile <filename>.")
    parser.add_argument("--outputfile", "-of",
                        help="--outputfile <filename> for decoded text.")


    parser.add_argument("--generate", "-g",
                        help="Generate a key of of size --modulus. If no" +
                        " modulus is provided then 2048 will be used.")
    parser.add_argument("--encryptionkey", "-ec",
                        help="The asymmetric key to use for encrypting.")
    parser.add_argument("--signingkey", "-sk",
                        help="The asymmetric key to use for signing.")
    parser.add_argument("--passphrase", "-p",
                        help="The passphrase to the singing key.")
    parser.add_argument("--modulus", "-md", help="Key modulus size.")


    parser.add_argument("--comparefiles", "-c",
                        help="Read back the first 512 pixels of an image.")
    args = parser.parse_args()

    steg = None
    plain_text_message = ""
    if args.generate:
        if not args.passphrase:
            print("A passphrase for the key must be provided.")
            exit(1)
        elif args.modulus:
            CryptoHelper.generateKeys(args.generate, args.passphrase,
                                      args.modulus)
        else:
            CryptoHelper.generateKeys(args.generate, args.passphrase)
    elif args.encode:
        if args.crypto:
            if (not args.inputimage or not args.outputimage
                or not(args.message or args.inputfile) or not
                args.encryptionkey or not args.signingkey or not args.passphrase):
                try:
                    steg = EncryptedSteganographer(inputFile=args.inputimage,
                                                outputfile=args.outputimage,
                                                recipientPublicKeyFileName=args.encryptionkey,
                                                sendersKeyPairFileName=args.signingkey,
                                                passphrase=args.passphrase)
                except KeyError as e:
                    print("The following error has occured: ")
                    print(e)
                    exit(1)
                try:
                    if args.inputfile:
                       steg.encrypt_and_encode_message_from_file(args.inputfile)
                    else:
                        steg.encrypt_and_encode_message(args.message)
                except IOError as e:
                    print("The following Error was encountered opening the " +
                          "message file.")
                    print(e)
                    exit(1)
            else:
                args.print_help()
        else:
            if (not args.inputimage or not args.outputimage
                or not(args.message or args.inputfile)):
                    try:
                        steg = Steganographer(inputFile=args.inputimage,
                                              outputFile=args.outputimage)
                    except KeyError as e:
                        print("The following error occured: ")
                        print(e)
                        exit(1)
                    try:
                        if args.inputfile:
                            steg.encode_image_from_file(args.inputfile)
                        else:
                            steg.encode_image(args.message)
                    except IOError as e:
                        print("The following error occured: ")
                        print(e)
                        exit(1)
            else:
                args.print_help()
    elif args.decode:
        if args.crypto:
            if (not args.inputimage or not args.outputimage
                or not args.encryptionkey or not args.signingkey 
                or not args.passphrase):
                try:
                    steg = EncryptedSteganographer(inputFile=args.inputimage,
                                                   recipientPublicKeyFileName=args.encryptionkey,
                                                   sendersKeyPairFileName=args.signingkey,
                                                   passphrase=args.passphrase)
                except KeyError as e:
                    print("The following error has occured: ")
                    print(e)
                    exit(1)
                try:
                    if args.outputfile:
                        steg.decrypt_and_decode_message_to_file(args.outputfile)
                        print("Message successfully written to " +
                               args.outputfile + ".")
                        exit(0)
                    else:
                        print("Message:\n")
                        print(steg.decrypt_and_decode_message())
                        exit(0)
                except IOError as e:
                    print("The following error was encountered: ")
                    print(e)
                    exit(1)
            else:
                args.print_help()
                exit(1)
        else:
            if (not args.inputimage or not args.outputimage):
                try:
                    steg = Steganographer(inputFile=args.inputimage)
                except KeyError as e:
                    print("The following error has occured: ")
                    print(e)
                    exit(1)
                try:
                    if args.outputfile:
                        steg.decode_image_to_file(args.outputfile)
                        print("Message successfully written to " +
                               args.outputfile + ".")
                        exit(0)
                    else:
                        print("Message:\n")
                        print(steg.decode())
                        exit(0)
                except IOError as e:
                    print("The following error was encountered: ")
                    print(e)
                    exit(1)
            else:
                args.print_help()
                exit(1)
    else:
        parser.print_help()
        exit(1)

    #Things went better than expected
    exit(0)