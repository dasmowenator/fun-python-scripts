import sys
import os
import re

DICTIONARY_FILE = 'words.txt' # '/usr/share/dict/words'
MIN_WORD_LENGTH = 3

def format_string(string):
    return re.sub(r'\s+', '', string).upper()

class Node:
    def __init__(self):
        self.connections = {}
        self.is_word = False

class Trie:
    def __init__(self, *words):
        self.root = Node()
        self.word_count = 0
        for word in words:
            self.add_word(word)
    def add_word(self, word):
        current_node = self.root
        for letter in word:
            if letter not in current_node.connections:
                current_node.connections[letter] = Node()
            current_node = current_node.connections[letter]
        current_node.is_word = True
        self.word_count += 1

def create_dictionary():
    file_path = os.path.join(os.getcwd(), DICTIONARY_FILE)
    print "Looking for dictionary file: %s" % (file_path)
    dictionary = Trie()
    with open(file_path, 'r') as dictionary_file:
        for line in dictionary_file:
            word = format_string(line)
            if len(word) >= MIN_WORD_LENGTH:
                dictionary.add_word(word)
    return dictionary

class Anagram:
    def __init__(self, anagram):
        self.anagram = anagram
        self.smallest_word_length = len(min(anagram.split(), key=len))
        self.largest_word_length = len(max(anagram.split(), key=len))
    def __str__(self):
        return self.anagram
    def __lt__(self, other): # makes this sortable
        if self.smallest_word_length == other.smallest_word_length:
            return self.largest_word_length < other.largest_word_length
        return self.smallest_word_length < other.smallest_word_length

def find_anagrams(root_node, current_node, input_string, current_string, ignore_indexes, anagrams):
    seen_letters_this_iteration = []
    for index, current_letter in enumerate(input_string):
        if index in ignore_indexes or current_letter in seen_letters_this_iteration:
            continue
        if current_letter in current_node.connections:
            seen_letters_this_iteration.append(current_letter)
            next_node = current_node.connections[current_letter]
            next_string = current_string + current_letter
            next_ignore_indexes = list(ignore_indexes)
            next_ignore_indexes.append(index)
            if next_node.is_word:
                if len(next_ignore_indexes) == len(input_string): # only add the anagram if it's complete, meaning the anagram uses all of the input characters
                    anagrams.append(Anagram(next_string))
                find_anagrams(root_node, root_node, input_string, next_string + ' ', next_ignore_indexes, anagrams)
            find_anagrams(root_node, next_node, input_string, next_string, next_ignore_indexes, anagrams)

##########################################################################
#########################  Run the Program ###############################
##########################################################################

if len(sys.argv) != 2:
    print "Usage: python %s \"word(s)\"" % (sys.argv[0])
    sys.exit(1)
input_string = format_string(sys.argv[1])
if not input_string:
    print "Usage: python %s \"word(s)\"" % (sys.argv[0])
    sys.exit(1)

print "Using input string: '%s'" % (input_string)
dictionary = create_dictionary()
print "Created dictionary with %s words" % (dictionary.word_count)

anagrams = []
find_anagrams(dictionary.root, dictionary.root, input_string, '', [], anagrams)
anagrams.sort(reverse=True)

print "\n\n"
for anagram in anagrams:
    print str(anagram)
