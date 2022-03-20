#Silas Clymer  2/14/21
#This is a Huffman Encoder and Decoder program
#Portions are adapted from Charles Cooley's code

from heapq import heappush, heappop

# Need some way to process binary data, this queue-like structure will work.
class BitBuffer():
    # external view is a string of 1s and 0s but internally stored in a more compact form
    def __init__(self, value=None):
        self.bits_before = ''   # buffer to hold bits being popped off
        self.data = bytes(0)    # buffer to hold the majority of the bits more efficiently
        self.bits_after = ''    # buffer to hold incoming bits as they are appended
        if type(value) == bytes:
            self.data = value
    def __str__(self): # convert the bytes into printable string of 1s and 0s
        return self.bits_before + ' ' + ''.join([('0000000' + bin(val)[2:])[-8:] for val in self.data]) + ' ' + self.bits_after
    def __len__(self):
        return len(self.bits_before) + len(self.bits_after) + 8 * len(self.data)
    def __bytes__(self):
        if len(self.bits_before) > 0: # this case is going to be very inefficient but isn't used except possibly for testing
            x = self.bits_before + ''.join([('0000000' + bin(val)[2:])[-8:] for val in self.data]) + self.bits_after
            x += '0' * (8-len(x)%8)
            return bytes([int(x[i:i + 8],2) for i in range(0, len(x), 8)])
        else:  # this is the case that really gets used for encoding and it is as efficient as possible
            if len(self.bits_after) > 0: # need to pad any incomplete byte so it gets added to data
                self.append('0' * (8-len(self.bits_after)%8))
            return self.data 
    def append(self, text): # add the string of 1s and 0s then collapse any groups of 8 into more compact form in data
        self.bits_after += str(text)
        while len(self.bits_after) > 7:
            self.data += bytes([int(self.bits_after[0:8],2)])
            self.bits_after = self.bits_after[8:]
    def append_chr(self, char): # store the character in its 16bit Unicode value (doesn't cover everything, but it's better than ASCII)
        self.append(('0000000000000000' + bin(ord(char))[2:])[-16:])
    def pop_bit(self):
        if len(self.bits_before) < 1:  # need at least one bit in the buffered string
            if len(self.data) > 0:  # pull some from the first byte of data
                self.bits_before += ('0000000' + bin(self.data[0])[2:])[-8:]
                self.data = self.data[1:]
            else: # no more full bytes so see if there are any individual bits that were recently pushed
                self.bits_before += self.bits_after
                self.bits_after = ''
        b = self.bits_before[0]  # pop and return either a 1 or a 0
        self.bits_before = self.bits_before[1:]
        return b
    def pop_chr(self):
        while len(self.bits_before) < 16 and len(self.data) > 0:  # need to get at least 16 bits in the buffered string
            self.bits_before += ('0000000' + bin(self.data[0])[2:])[-8:] # pull a byte out of data
            self.data = self.data[1:]
        if len(self.bits_before) < 16:  # not enough bits in the bytes data so what about the ones recently pushed? (probably still not enough)
            self.bits_before += self.bits_after
            self.bits_after = ''
        c = chr(int(self.bits_before[0:16],2))  # now decode the first 16 bits as a character and return it
        self.bits_before = self.bits_before[16:]
        return c


# A simple tree node structure for the Huffman Coding algorithms
class TreeNode():

    # constructor for the nodes
    def __init__(self, value=None, weight=None, left=None, right=None):
        self.value = value
        self.weight = weight
        self.left = left
        self.right = right

    # comparison operator for < so the heap knows how to sort the nodes
    def __lt__(self, other):
        if self.weight != other.weight: # primary sorting is based on weight
            return self.weight < other.weight
        else: # secondary sort on letter values in code-point order
            return (self.value or '\udddd') < (other.value or '\udddd')
            # '\udddd' is my choice for pseudo-eof, it's big and illegal

    # maybe not really needed, but good to implement along with __lt__
    def __eq__(self, other):
        return self.weight == other.weight

    # this only converts a node to a string, not the entire tree recursively
    def __str__(self):
        if self.value == '\udddd':
            return "EOF " + str(self.weight)
        elif self.value:
            return "LEAF " + self.value + " " + str(self.weight)
        else:
            return "INODE " + str(self.weight)
        

        


# the encoding logic
def huff_encode(filename):

    with open(filename, 'r') as file:
        text = file.read()
        
    def build_freq(text):
        freq = {} 
        for i in text: 
            if i in freq: 
                freq[i] += 1
            else: 
                freq[i] = 1
        return freq

    def build_forest_from_frequencies(forest, freq):
        for char in freq:
            #print(char, freq[char])
            tree = TreeNode(char, freq[char])
            heappush(forest, tree)
        #print(forest)
        return forest
        
    def merge_trees(forest):
        while(len(forest) > 1):
            t1 = heappop(forest)
            #print(t1.weight)
            t2 = heappop(forest)
            #print(t2.weight)
            merged = TreeNode(None, t1.weight + t2.weight, t1, t2)
            #print(str(merged))
            #print(merged.weight,'\n')
            heappush(forest, merged)
        return forest[0]

    def encode_into_header(node, data):
        if node:
            if node.value:
                data.append('1')
                data.append_chr(node.value)
                #print('1' + str(node))
            else:
                data.append('0')
                #print('0' + str(node))
            data = encode_into_header(node.left, data)
            data = encode_into_header(node.right, data)
        return data

    def build_code_table(node, path, table):
        if node:
            if node.value:
                table[node.value] = path
            #print(str(node))
            table = build_code_table(node.left, path + '0', table)
            table = build_code_table(node.right, path + '1', table)
        return table

    freq = build_freq(text)

    # make a tree node for each symbol and push it into the forest heap
    forest = [] # this will be our heap (i.e. priority queue) of trees
    build_forest_from_frequencies(forest, freq)
    # append a pseudo-eof marker to the heap with the lowest weight (0)
    heappush(forest, TreeNode('\udddd', 0)) # "\udddd" is an invalid unicode character!

    # merge smallest pairs from forest until down to one big tree
    encoding_tree = merge_trees(forest)

    # set up buffer for the output
    encoded_data = BitBuffer()
    # store the tree into the buffer as the header using append("0"),
    # append("1") and append_chr(tree.value) methods in the traversal function
    encoded = encode_into_header(encoding_tree, encoded_data)
    # first parameter is input, second is for the output

    # create the encoding code table (i.e. dictionary) from the tree (recursively)
    code_table = {}
    build_code_table(encoding_tree, "", code_table)
    # first parameter initially passed the root of the tree
    # second parameter records the path as you recursively traverse the tree
    # when you get to the leaf, that path is the encoding for the leaf's value
    # so when calling down for a child, add to the path
    # at the leaf, add an entry to the code_table

    # encode the input
    for symbol in text:
        encoded.append(code_table[symbol])
    encoded.append(code_table['\udddd']) # add the pseudo-eof character

    # output the result
    with open(filename + '.huff.txt', 'wb') as file:
        file.write(bytes(encoded))  # padding to get to full bytes is automatic


# the decoding logic
def huff_decode(filename):
    with open(filename + '.huff.txt', 'rb') as file:
        coded = BitBuffer(file.read()) # reading binary file into the buffer

    #print(coded)
    def rebuild_tree(data):
        nodekind = data.pop_bit()
        if nodekind == '0':
            node = TreeNode(None, 0, rebuild_tree(data), rebuild_tree(data))
        if nodekind == '1':
            node = TreeNode(data.pop_chr(), 0)
        return node
       
    def trav(node):
        res = ''
        if node:
            print(str(node))
            res = trav(node.left)
            res = res + trav(node.right)
        return res
    
    # reconstruct a decode tree from the header data using pop_bit() and pop_chr()
    decode_tree = rebuild_tree(coded)
    #print(trav(decode_tree))
    
    # prepare for the decode cycle
    result = "" # a simple character buffer to hold the decoded data
    t = decode_tree # we haven't read any real data so start at he top of the tree
    while True:
        direction = coded.pop_bit()
        if direction == '0':
            t = t.left
        else:
            t = t.right
        if t.value:
            if t.value == '\udddd':
                break
            else:
                result = result + t.value
                #print(t.value)
                t = decode_tree
       
        # pop a bit and traverse down the tree appropriately
        # if you land on the pseudo-eof character, you're done
        # if you land on any other leaf node, store the value and move t back to the top.

    #after you've seen the pseudo-eof you can output the translated result
    with open(filename + '.out.txt', 'w') as file:
        file.write(result)



huff_encode("huff.py")

huff_decode("huff.py")

