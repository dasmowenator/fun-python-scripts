import sys
import re
import os
import time
import random
from urlparse import urljoin
try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print '"BeautifulSoup4" module is not installed, run this command to install:'
    print 'Mac/Linux: sudo easy_install -U beautifulsoup4'
    print 'Windows: pip install beautifulsoup4'
    sys.exit(1)
try:
    import requests
except ImportError:
    print '"requests" module is not installed, run this command to install:'
    print 'Mac/Linux: sudo easy_install -U requests'
    print 'Windows: pip install requests'
    sys.exit(1)


DEBUG = False # flag for debug logging
REPEAT_PATTERN = re.compile(r'^(.*) [\[\(]?[xX]?\d+[xX]?[\]\)]?$')

TOP_100_URL = 'http://www.songlyrics.com/top100.php'
ARTIST_SEARCH_URL_FORMAT = "http://search.azlyrics.com/search.php?q=%s&p=0&w=artists"
GENRE_LIST_URL = 'http://www.songlyrics.com/musicgenres.php'
EXPECTED_COMMENT = 'Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement'
HTTP_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36'}

MIN_LINES_PER_VERSE = 3
MAX_LINES_PER_VERSE = 6 # this will also be the number of songs fetched

MIN_VERSES_PER_SONG = 8
MAX_VERSES_PER_SONG = 12


# prints the list of verses to stdout, where each verse is a list of lyrics lines
def print_verses(verses):
    for verse in verses:
        for line in verse:
            print line
        print ''

# prints a table of width 5 on multiple lines
def pretty_print(print_list):
    max_width = len(max(print_list, key=len)) + 2
    pretty_string = '    '
    for index, value in enumerate(print_list):
        if index != 0 and index % 5 == 0:
            print pretty_string
            pretty_string = '    '
        pad_length = max_width - len(value)
        pretty_string += value + (' ' * pad_length)
    print pretty_string

# returns a list of lyric verses for the song from the given URL,
# where each verse is a list of lyrics lines
def get_verses_from_song_url(url):
    all_text = None
    if 'songlyrics.com' in url:
        response = requests.get(url, headers=HTTP_HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        elem = soup.find(id='songLyricsDiv')
        all_text = elem.find_all(text=True)
    elif 'azlyrics.com' in url:
        response = requests.get(url, headers=HTTP_HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        elem = soup.find(string=lambda text: isinstance(text, Comment) and EXPECTED_COMMENT in text)
        elem = elem.parent
        all_text = elem.find_all(text=True)
    else:
        raise RuntimeError("Invalid song URL: %" % (url))
    
    verses = []
    just_added_verse = False
    verse = []
    for line in all_text:
        line = line.strip()
        if line:
            if line.startswith('(') or line.startswith('[') or line.startswith('{') or line.startswith('/') or line.lower().startswith('produced by') or re.match(r'\d+[xX]', line) or 'azlyrics.com content' in line:
                continue # ignore these lines
            match = REPEAT_PATTERN.match(line)
            if match: # remove the [x4] or anything like that at end of lines
                if DEBUG: print "(DEBUG) Converting line \"%s\" to \"%s\"" % (line, match.group(1))
                line = match.group(1)
            verse.append(line.encode('utf8'))
            just_added_verse = False
        elif verse and not just_added_verse:
            verses.append(verse)
            verse = []
            just_added_verse = True
    if verse and not just_added_verse:
        verses.append(verse)
    
    if DEBUG:
        print "(DEBUG) Found %s verses" % (len(verses))
    return verses

# represents a song
class Song:
    def __init__(self, artist, title, url):
        self.artist = artist.encode('utf8')
        self.title = title.encode('utf8')
        self.url = url
        self.verses = get_verses_from_song_url(url)
    def __str__(self):
        return "\"%s\" by %s" % (self.title, self.artist)

# parses the list of genres from the website
def get_genre_list():
    response = requests.get(GENRE_LIST_URL, headers=HTTP_HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='tracklist')
    genre_elems = table.find_all(lambda elem: elem.name == 'a' and elem.parent.name == 'td' and elem.parent['class'] == ['td-item', 'td-text-big'])
    genres_to_urls = {}
    for genre_elem in genre_elems:
        genre_name = genre_elem.text.encode('utf8')
        if (genre_name.endswith(';')): # not sure why, but sometimes the name ends with a semicolon when it shouldn't
            genre_name = genre_name[:-1]
        genre_url = urljoin(GENRE_LIST_URL, genre_elem['href'])
        if DEBUG: print "(DEBUG) Adding genre \"%s\" with URL \"%s\" from: %s" % (genre_name, genre_url, genre_elem)
        genres_to_urls[genre_name] = genre_url
    return genres_to_urls

# returns a list of Songs from the songlyrics.com website
def choose_songs_from_songlyrics(url): # only for songlyrics.com
    response = requests.get(url, headers=HTTP_HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='tracklist')
    song_links = table.find_all(lambda elem: elem.name == 'a' and elem.text and len(list(elem.parent.parent.children)) == 2)
    song_links = random.sample(song_links, MAX_LINES_PER_VERSE) # choose a few songs at random
    songs = []
    for song_link in song_links:
        if DEBUG: print "(DEBUG) Using song: %s" % (song_link)
        song_artist = song_link.parent.parent.find('span').text
        song_title = song_link.text
        song_url = urljoin(url, song_link['href'])
        songs.append(Song(song_artist, song_title, song_url))
    return songs

# returns a list of Songs from the azlyrics.com website
def choose_songs_from_azlyrics(artist, url): # only for azlyrics.com
    response = requests.get(url, headers=HTTP_HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    div = soup.find(id='listAlbum')
    song_links = div.find_all(lambda elem: elem.name == 'a' and elem.has_attr('href') and 'lyrics/' in elem['href'])
    song_links = random.sample(song_links, MAX_LINES_PER_VERSE) # choose a few songs at random
    songs = []
    for song_link in song_links:
        if DEBUG: print "(DEBUG) Using song: %s" % (song_link)
        song_title = song_link.text
        song_url = urljoin(url, song_link['href'])
        songs.append(Song(artist, song_title, song_url))
    return songs

# returns list of songs from the given artist
def find_songs_from_artist():
    artist = re.sub(r'\s+', '+',raw_input('Artist Name: ').strip())
    artist_search_url = ARTIST_SEARCH_URL_FORMAT % (artist)
    if DEBUG: print "(DEBUG) Using artist search URL: %s" % (artist_search_url)
    response = requests.get(artist_search_url, headers=HTTP_HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    artist_url = table.find('a')['href']
    artist_url = urljoin(artist_search_url, artist_url)
    
    if DEBUG: print "(DEBUG) Using artist URL: %s" % (artist_url)
    return choose_songs_from_azlyrics(artist, artist_url)

# returns list of songs from the given genre
def find_songs_from_genre():
    genres_to_urls = get_genre_list()
    sorted_genre_list = sorted(genres_to_urls, key=genres_to_urls.get)
    print "Available genres are:"
    pretty_print(sorted_genre_list)
    
    raw_genre = raw_input('Genre: ').strip()
    lower_genre = raw_genre.lower()
    genre_url = None
    for key, value in genres_to_urls.items():
        if lower_genre == key.lower():
            genre_url = value
            break
    if not genre_url:
        raise RuntimeError("Invalid genre: \"%s\"" % (raw_genre))
    
    if DEBUG: print "(DEBUG) Using genre URL: %s" % (genre_url)
    return choose_songs_from_songlyrics(genre_url)

# returns list of songs on the Top 100 list
def find_songs_from_top_100():
    if DEBUG: print "(DEBUG) Using top 100 URL: %s" % (TOP_100_URL)
    return choose_songs_from_songlyrics(TOP_100_URL)

# shuffles lyrics from the given songs to generate a new song
def compose_from_songs(songs):
    num_verses = random.randint(MIN_VERSES_PER_SONG, MAX_VERSES_PER_SONG)
    verses = []
    for i in range(0, num_verses):
        num_lines_in_verse = random.randint(MIN_LINES_PER_VERSE, MAX_LINES_PER_VERSE)
        verse = []
        for j in range(0, num_lines_in_verse):
             # select a random line from a random song
            random_song = random.choice(songs)
            random_verse = random.choice(random_song.verses)
            random_line = random.choice(random_verse)
            verse.append(random_line)
        verses.append(verse)
    return verses

##########################################################################
#########################  Run the Program ###############################
##########################################################################

songs = None
while True:
    raw_source = raw_input('Do you want to look up songs by artist, genre, or top 100? ').strip()
    lower_source = raw_source.lower()
    if not lower_source:
        continue
    elif lower_source == 'artist':
        songs = find_songs_from_artist()
        break
    elif lower_source == 'genre':
        songs = find_songs_from_genre()
        break
    elif lower_source == 'top 100' or lower_source == 'top100':
        songs = find_songs_from_top_100()
        break
    else:
        print "Invalid option \"%s\" please try again...\n" % (raw_source)
        continue

print "\n\nComposing song using:"
for song in songs:
    print "  %s" % (str(song))
print "\n\n"
time.sleep(1)

new_song_verses = compose_from_songs(songs)

print_verses(new_song_verses)

