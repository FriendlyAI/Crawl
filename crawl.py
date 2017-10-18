#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Andrew Li
Crawl: Reddit Scraping and Analysis
Term Project
15-112 Summer 2017
Section B
"""

import random
import re
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

import praw
import prawcore

REDDIT = praw.Reddit(client_id='wUZpv15zMB-TTQ',
                     client_secret='8h8PaAufQ4xjrpuH6wcwI14pzyU',
                     user_agent='MacOS:Crawl:v1.0 (by /u/Crawl112)',
                     username='Crawl112',
                     password='15112cmu')

# Whitelist from http://www.ranks.nl/stopwords
WHITELIST = set()
try:
    with open("whitelist.txt", "r") as f:
        for stopword in f.readlines():
            WHITELIST.add(stopword.strip())
except FileNotFoundError:
    print('ERROR: whitelist.txt file missing from folder.')

# URL_RE and TOKEN_RE patterns from https://github.com/rhiever
URL_RE = re.compile(r'^(.*http(s)?://|www.)|.(com|it|net|org)($|/)')
TOKEN_RE = re.compile(r"[^\W_]+(?:\'(?:d|ll|m|re|s|t|ve))?")

MARKOV_RE = re.compile(r"[\[(\"']?[^\W_]+(?:\'(?:d|ll|m|re|s|t|ve))?[.?\]/):,\"']?")
REFERENCE_RE = re.compile(r'/?[ur]/\w+\Z')


# Adapted from www.andreas-jung.com
def timeit(func):
    def timed(*args, **kw):
        ts = time.time()
        result = func(*args, **kw)
        te = time.time()

        with open('log.txt', 'a+') as file:
            file.write('%r took %2.2f sec\n' % (func.__name__, te - ts))
        return result

    return timed


class Window:
    def __init__(self, master):
        # Window initialization

        self.master = master
        self.master.resizable(width=False, height=False)
        screen_width = master.winfo_screenwidth()  # width of the screen
        screen_height = master.winfo_screenheight()  # height of the screen
        self.width = 800
        self.height = 600
        self.x_center = screen_width / 2 - self.width / 2
        self.y_center = screen_height / 2 - self.height / 2
        self.master.geometry('%dx%d+%d+%d' % (self.width, self.height, self.x_center, self.y_center))
        self.master.title('Crawl: Reddit Scraping and Analysis')
        self.master.bind('<Key>', self.help)

        # Initialization

        self.corpus_objects = []
        self.corpus_objects_id = []
        self.markov_cache = ''

        # Visualize button

        self.visualize = tk.Button(self.master, text='Visualize Data', command=self.visualize_data)
        self.visualize.place(x=self.width / 2, y=self.height - 40, anchor='c')

        # Icon
        self.image = tk.PhotoImage(file='icon.gif')
        self.image2 = tk.PhotoImage(file='loading.gif')
        self.icon = tk.Label(self.master, image=self.image)
        self.icon.pack()

        # Corpus type

        self.type_label = tk.Label(self.master, text='Type:')
        self.type_label.place(x=300, y=206)

        self.corpus_type_variable = tk.StringVar(self.master)
        self.corpus_types = ['Subreddit', 'User']
        self.corpus_type_variable.set(self.corpus_types[0])

        self.corpus_type = tk.OptionMenu(self.master, self.corpus_type_variable, *self.corpus_types,
                                         command=self.changed_type)
        self.corpus_type.configure(width=14)
        self.corpus_type.pack()

        # Corpus name

        self.name_label = tk.Label(self.master, text='Name:')
        self.name_label.place(x=270, y=233)

        self.corpus_name = tk.Entry(self.master, width=20)
        self.corpus_name.bind('<Return>', func=self.textbox_enter)
        self.corpus_name.configure(bd=0, highlightbackground='DarkOrchid1', highlightcolor="DeepPink1", font="Menlo")
        self.corpus_name.pack()

        # Submission sort

        self.subsort_label = tk.Label(self.master, text='Submissions By:')
        self.subsort_label.place(x=234, y=259)

        self.sort_type_variable = tk.StringVar(self.master)
        self.sort_types = ['hot', 'top', 'new', 'controversial']
        self.sort_type_variable.set(self.sort_types[0])
        self.sort_type = tk.OptionMenu(self.master, self.sort_type_variable, *self.sort_types)
        self.sort_type.configure(width=14)
        self.sort_type.pack()

        # Comment sort

        self.comsort_label = tk.Label(self.master, text='Subreddit Comments By:')
        self.comsort_label.place(x=182, y=289)

        self.comment_sort_type_variable = tk.StringVar(self.master)
        self.comment_sort_types = ['best', 'top', 'new', 'controversial']
        self.comment_sort_type_variable.set(self.comment_sort_types[0])

        self.comment_sort_type = tk.OptionMenu(self.master, self.comment_sort_type_variable, *self.comment_sort_types)
        self.comment_sort_type.configure(width=14)
        self.comment_sort_type.pack()

        # Post limit for subreddits

        self.post_limit_label = tk.Label(self.master, text='Subreddit Post Limit:')
        self.post_limit_label.place(x=250, y=316)

        self.post_limit = tk.Entry(self.master, width=3)
        self.post_limit.insert(0, 10)
        self.post_limit.bind('<Return>', func=self.textbox_enter)
        self.post_limit.configure(bd=0, highlightbackground='DarkOrchid1', highlightcolor='DeepPink1', font='Menlo')
        self.post_limit.pack()

        # Add button

        self.add = tk.Button(self.master, text='Add', command=self.add_corpus)
        self.add.pack()

        # Listbox of analyzed corpuses

        self.corpus_list = tk.Listbox(self.master, selectmode='single')
        self.corpus_list.configure(width=30, height=8)
        self.corpus_list.pack()

        # Delete button

        self.delete = tk.Button(self.master, text='Delete Analysis', command=self.delete_corpus)
        self.delete.pack()

        # Help menu
        self.in_help = False
        self.help()

        # Word frequency more info
        self.circles = {}
        self.border = None
        self.text = None

    def show_master(self, _=None, manual=None):
        if manual:
            manual.destroy()
        self.in_help = False
        self.master.deiconify()  # Make master visible

    def help(self, event=None):
        if not self.in_help and (not event or event.keysym == 'Tab'):
            self.in_help = True
            self.master.withdraw()
            help_window = tk.Toplevel()
            help_window.geometry('%dx%d+%d+%d' % (self.width, self.height, self.x_center, self.y_center))
            help_window.bind('<Destroy>', self.show_master)
            help_window.bind('<Return>', lambda _: self.show_master(manual=help_window))

            # Instructions
            welcome_label = tk.Label(help_window, text='Welcome to Crawl!', font='Futura 24 bold', fg='orange red')
            welcome_label.pack()
            help_label = tk.Label(help_window,
                                  justify='left',
                                  text='Instructions:\n\n'
                                       '1. Choose "User" or "Subreddit" as your desired analysis type.\n\n'
                                       '2. Enter the name of your desired page. Ex. "askreddit"\n\n'
                                       '3. Choose sorting options for the submissions.\n\n'
                                       '4. If you chose to analyze a subreddit, you can also choose comment sorting\n'
                                       'and a limit for the number of submissions you analyze.\n\n'
                                       '5. Click the "Add" button and wait for analysis to complete. This may take up\n'
                                       'to a minute depending on the popularity and limit.\n\n'
                                       '6. After adding, the subreddit or user will automatically be added to a list\n'
                                       'of analyzed pages. These are automatically stored and can be removed at any\n'
                                       'time by selecting the desired subreddit or user and clicking the "Delete\n'
                                       'Analysis" button.\n\n'
                                       '7. Click the "Visualize Data" button to enter a window for visualizing the\n'
                                       'subreddits and users you have added. Note that there is a preloaded subreddit\n'
                                       'for offline or control use.\n\n'
                                       'Note: Markov Chains can be posted to the bot account /u/Crawl112.\n\n'
                                       '(This menu can be accessed again from the main menu by pressing "Tab").\n\n')
            help_label.pack()

            # OK button

            ok_button = tk.Button(help_window, text='OK', command=lambda: self.show_master(manual=help_window))
            ok_button.pack()

    def changed_type(self, event):
        # Disable subreddit comment sort and subreddit post limit if analyzing a user
        if event == 'User':
            self.comment_sort_type.configure(state='disabled')
            self.comsort_label.configure(fg='gray50')
            self.post_limit.configure(state='disabled')
            self.post_limit_label.configure(fg='gray50')

        else:
            self.comment_sort_type.configure(state='normal')
            self.comsort_label.configure(fg='black')
            self.post_limit.configure(state='normal')
            self.post_limit_label.configure(fg='black')

    def textbox_enter(self, _):
        # Add corpus and clear textbox
        self.add_corpus()
        return 'break'

    def delete_corpus(self):
        # Delete corpus completely
        selection = self.corpus_list.curselection()
        if selection:
            self.corpus_list.delete(selection)
            remove_index = len(self.corpus_objects) - selection[0] - 1
            del self.corpus_objects[remove_index]
            del self.corpus_objects_id[remove_index]

    def add_corpus(self):
        type_ = self.corpus_type_variable.get()
        name = self.corpus_name.get().strip().lower()
        limit = self.post_limit.get().strip()

        try:
            # Test that user or subreddit exists
            if type_ == 'User':
                _ = REDDIT.redditor(name).fullname

            else:
                for _ in REDDIT.subreddit(name).top(limit=1):
                    break

        except (prawcore.exceptions.Redirect, prawcore.exceptions.NotFound, prawcore.exceptions.Forbidden):
            tk.messagebox.showerror(title='Error',
                                    message='Error: Couldn\'t find {0} "{1}".'.format(type_.lower(), name))

        except TypeError:
            tk.messagebox.showerror(title='Error',
                                    message='Error: Please enter a {0}.'.format(type_.lower()))

        else:
            sort = self.sort_type_variable.get()
            if type_ == 'User':
                comment_sort = None
                prefix = 'u'
                limit = None

            else:
                comment_sort = self.comment_sort_type_variable.get()
                prefix = 'r'

            corpus_id = f'/{prefix}/{name} ({sort}' \
                        f'{", " +  comment_sort if comment_sort else ""}{", " + limit if limit else ""})'

            # ID for display/storage
            if corpus_id in self.corpus_objects_id:  # Already added
                tk.messagebox.showinfo(title='Duplicate',
                                       message='Can\'t add duplicate {0} named "{1}".'
                                       .format(type_.lower(), name))

            elif type_ == 'Subreddit' and not limit.isdigit():
                tk.messagebox.showinfo(title='Error',
                                       message='Invalid limit: "{}".'
                                       .format(limit if limit else '<NONE>'))

            else:
                # Show loading image and label
                wait_label = tk.Label(self.master, text='please wait...', fg='red')
                wait_label.place(x=710, y=580)
                self.icon.configure(image=self.image2)
                self.icon.image = self.image2
                self.master.update()

                # Create and add new corpus
                limit = int(limit) if limit else None
                new_corpus = CorpusMetadata(type_, name, sort, comment_sort, limit)
                self.corpus_objects.append(new_corpus)
                self.corpus_objects_id.append(corpus_id)
                self.corpus_list.insert(0, corpus_id)

                # Show completed
                wait_label.destroy()
                self.icon.configure(image=self.image)
                self.icon.image = self.image
                self.master.update()
                tk.messagebox.showinfo(title='Finished',
                                       message='Your {0} has been analyzed.'.format(type_.lower()))

            self.corpus_name.delete(0, 'end')  # Clear textbox
            self.post_limit.delete(0, 'end')
            self.post_limit.insert(0, 10)

    def visualize_data(self):

        def selection_type():
            canvas.delete('all')
            type_ = analysis_type_variable.get()
            if type_ == 'Word Frequency':
                if obj_variable.get() == 'Preloaded (/r/askreddit)':
                    create_word_cloud()
                else:
                    create_word_cloud(self.corpus_objects[self.corpus_objects_id.index(obj_variable.get())])
            elif type_ == 'Link Types':
                create_link_type_graph()
            elif type_ == 'Markov Chain':
                if obj_variable.get() == 'Preloaded (/r/askreddit)':
                    get_markov_chain()
                else:
                    get_markov_chain(self.corpus_objects[self.corpus_objects_id.index(obj_variable.get())])

        def create_word_cloud(corpus=None):
            self.circles = {}
            start = 10
            sum_freq = 0
            total_freq = 0
            # Equidistant colors from stackoverflow.com
            colors_rgb = [(255, 50, 50), (255, 173, 50), (214, 255, 50), (91, 255, 50), (50, 255, 132),
                          (50, 255, 255), (50, 132, 255), (91, 50, 255), (214, 50, 255), (255, 50, 173)]
            colors = ['#%02x%02x%02x' % (r, b, g) for r, g, b in colors_rgb]
            if not corpus:
                words = {}
                top_keys = []
                count = 0
                with open('preloaded_corpus.txt', 'r') as file:
                    for line in file.readlines():
                        key, val = line.split('\t')
                        top_keys.append(key)
                        val = int(val)
                        words[key] = val
                        total_freq += val
                        if count < 10:
                            sum_freq += val
                            count += 1
            else:
                words = corpus.words
                top_keys = list(reversed(sorted(words, key=words.get)))
                total_freq = sum(words.values())
                for i in range(10):
                    sum_freq += corpus.words[top_keys[i]]
            random.shuffle(colors)
            draw_word_bubbles(start, sum_freq, total_freq, words, top_keys, colors)
            canvas.update()

        def draw_word_bubbles(start, sum_freq, total_freq, words, top_keys, colors):
            for i in range(10):
                word, freq = top_keys[i], words[top_keys[i]]
                proportion = freq / sum_freq
                radius = (self.width - 100) * proportion / 2
                start += max(radius, 15)
                if i % 2 == 0:
                    canvas.create_oval(start - radius, 200 - radius,
                                       start + radius, 200 + radius,
                                       fill=colors[i], width=0)
                    canvas.create_text(start, 200, text=word.center(8) + '\n({0:.2f}%)'.format(freq / total_freq * 100))
                    self.circles[(start, 200, radius)] = (freq, total_freq)
                else:
                    canvas.create_oval(start - radius, 300 - radius,
                                       start + radius, 300 + radius,
                                       fill=colors[i], width=0)
                    canvas.create_text(start, 300, text=word.center(8) + '\n({0:.2f}%)'.format(freq / total_freq * 100))
                    self.circles[(start, 300, radius)] = (freq, total_freq)
                start += max(radius, 15)

        def more_info(event):
            if self.border and self.text:
                canvas.delete(self.border)
                canvas.delete(self.text)
            for (x, y, radius), (freq, total) in self.circles.items():
                if (event.x - x) ** 2 + (event.y - y) ** 2 < radius ** 2:
                    event.x = min(max(5, event.x - 120), self.width - 245)
                    event.y = max(5, event.y - 40)
                    self.border = canvas.create_rectangle(event.x, event.y,
                                                          event.x + 240, event.y + 20,
                                                          fill='white')
                    self.text = canvas.create_text(event.x + 120, event.y + 10,
                                                   text='Occurances/All Words: {0}/{1}'.format(freq, total))
                    return

        def create_link_type_graph():
            margin = 50
            num_bars = len(self.corpus_objects) + 1
            bar_width = (self.width - margin * (num_bars + 1)) / num_bars
            start_x = margin
            start_y = 10
            colors = {'Self Text': 'orange', 'Images': 'green', 'Tweets': 'cyan', 'Videos': 'red', 'Links': 'yellow'}
            with open('preloaded_domains.txt', 'r') as file:
                for line in file.readlines():
                    domain, freq = line.split('\t')
                    freq = int(freq)
                    if freq > 0:
                        canvas.create_rectangle(start_x, start_y,
                                                start_x + bar_width, start_y + 4 * freq,
                                                fill=colors.get(domain), width=0)
                        canvas.create_text(start_x + bar_width / 2, start_y + 2 * freq,
                                           text=domain + f' ({freq}%)', font='TkDefaultFont 10')
                        start_y += 4 * freq
            canvas.create_text(start_x + bar_width / 2, start_y + 15, text='Preloaded (/r/askreddit)',
                               font='TkDefaultFont 10')
            start_x += margin + bar_width
            start_y = 10
            for corpus in self.corpus_objects:
                total = sum(corpus.domains.values())
                for domain in reversed(sorted(corpus.domains.keys(), key=corpus.domains.get)):
                    freq = int(corpus.domains[domain] / total * 100)
                    if freq > 0:
                        canvas.create_rectangle(start_x, start_y,
                                                start_x + bar_width, start_y + 4 * freq,
                                                fill=colors.get(domain), width=0)
                        canvas.create_text(start_x + bar_width / 2, start_y + 2 * freq,
                                           text=domain + f' ({freq}%)', font='TkDefaultFont 10')
                        start_y += 4 * freq
                name = '/{0}/{1}'.format('u' if corpus.type_ == 'User' else 'r', corpus.name)
                canvas.create_text(start_x + bar_width / 2, start_y + 15, text=name,
                                   font='TkDefaultFont 10')
                start_x += margin + bar_width
                start_y = 10

        def get_markov_chain(corpus=None):
            post.configure(state='normal')
            if corpus:
                markov_chain_sentence = generate_markov_chain(corpus.start_words, corpus.word_chain)
                canvas.create_text(self.width / 2, 100, text=markov_chain_sentence, width=500,
                                   font='TkDefaultFont 20')
            else:
                words = []
                with open('preloaded_comments.txt', 'r') as file:
                    for line in file.readlines():
                        words.append(line)
                word_chain = generate_word_chain(words)
                start_words = [key for key in word_chain.keys() if key[0][0].isupper()]
                markov_chain_sentence = generate_markov_chain(start_words, word_chain)
                canvas.create_text(self.width / 2, 100, text=markov_chain_sentence, width=500,
                                   font='TkDefaultFont 20')
            self.markov_cache = markov_chain_sentence

        def post_markov_chain():
            # Submit markov chain to bot account
            url_label.place(x=415, y=30)
            posted_label.place(x=10, y=30)
            title = obj_variable.get().split()[0]
            if title == 'Preloaded':
                title = '/r/askreddit'
            if self.markov_cache:
                REDDIT.subreddit('u_Crawl112').submit(title + ' says:', selftext=self.markov_cache)

        def open_bot_page(_):
            webbrowser.open_new(r'https://www.reddit.com/user/Crawl112/')

        def changed_analysis_type(event):
            # Disable corpus chooser if analyzing all
            self.markov_cache = ''
            if event == 'Link Types':
                self.circles = {}
                objects.configure(state='disabled')
                post.configure(state='disabled')
                post.grid_forget()
                posted_label.place_forget()
                url_label.place_forget()
            elif event == 'Markov Chain':
                self.circles = {}
                objects.configure(state='normal')
                post.grid(row=0, column=3)
            else:
                objects.configure(state='normal')
                post.configure(state='disabled')
                post.grid_forget()
                posted_label.place_forget()
                url_label.place_forget()

        self.master.withdraw()  # Make master invisible
        visualization = tk.Toplevel()
        visualization.resizable(width=False, height=False)

        visualization.geometry('%dx%d+%d+%d' % (self.width, self.height, self.x_center, self.y_center))
        visualization.title('Visualization')
        visualization.bind('<Destroy>', self.show_master)

        # Type of analysis

        analysis_type_variable = tk.StringVar(visualization)
        analysis_types = ['Word Frequency', 'Link Types', 'Markov Chain']
        analysis_type_variable.set('Word Frequency')

        analysis_type = tk.OptionMenu(visualization, analysis_type_variable, *analysis_types,
                                      command=changed_analysis_type)
        analysis_type.configure(width=16)
        analysis_type.grid(row=0, column=0)

        # Object to analyze

        obj_variable = tk.StringVar(visualization)
        obj_variable.set('Preloaded (/r/askreddit)')  # Default object is first added

        objects = tk.OptionMenu(visualization, obj_variable, *['Preloaded (/r/askreddit)'] + self.corpus_objects_id)
        objects.configure(width=30)
        objects.grid(row=0, column=1)

        # Visualize button

        visualize = tk.Button(visualization, text='Visualize', command=selection_type)
        visualize.grid(row=0, column=2)

        canvas = tk.Canvas(visualization, width=self.width, height=self.height)
        canvas.bind('<Button-1>', more_info)
        canvas.place(x=0, y=100)

        # Post Markov Chain button

        post = tk.Button(visualization, text='Post to /u/112Crawl', command=post_markov_chain)
        post.grid(row=0, column=3)
        post.grid_forget()
        post.configure(state='disabled')

        posted_label = tk.Label(visualization, text='Posted your Markov Chain to /u/Crawl112!'
                                                    ' Check out all posts at:')
        url_label = tk.Label(visualization, text='reddit.com/u/Crawl112', fg='blue', cursor='top_right_corner',
                             font='TkDefaultFont 13 underline')
        url_label.bind('<Button-1>', open_bot_page)


class CorpusMetadata:
    def __init__(self, type_, name, sort, comment_sort, limit):

        # Initialization

        self.words = {}
        self.domains = {'Self Text': 0, 'Images': 0, 'Tweets': 0, 'Videos': 0, 'Links': 0}
        self.type_ = type_
        self.name = name
        self.comment_sort = comment_sort
        self.sort = sort
        self.corpus = []
        self.limit = limit

        # Log

        self.log()

        # Analyze data

        self.get_corpus()
        self.count_domains()
        self.count_words()
        self.word_chain = {}
        self.word_chain = generate_word_chain(self.corpus)
        self.start_words = [key for key in self.word_chain.keys() if key[0][0].isupper()]

    def log(self):
        with open('log.txt', 'a+') as file:
            file.write('\nType: {0}\nName: {1}\nSubmission Sort: {2}\nComment Sort: {3}\n'.format
                       (self.type_, self.name, self.sort, self.comment_sort))

    @timeit
    def get_corpus(self):
        if self.type_ == 'User':
            self.corpus = get_corpus_from_user(self.name, self.sort)
        elif self.type_ == 'Subreddit':
            self.corpus = get_corpus_from_subreddit(self.name, self.sort, self.comment_sort, self.limit)

    @timeit
    def count_words(self):
        for token in get_tokens(self.corpus):
            self.words[token] = self.words.get(token, 0) + 1
        for word in self.words.keys():
            if word.endswith('s'):
                count = self.words[word]
                singular = word[:-1]
                if self.words.get(singular):
                    # Combine plurals and singulars into the most-used form
                    if self.words[singular] > count:
                        self.words[singular] += self.words[word]
                        self.words[word] = 0
                    else:
                        self.words[word] += self.words[singular]
                        self.words[singular] = 0

    @timeit
    def count_domains(self):
        images = ['i.imgur.com', 'imgur.com', 'gfycat.com', 'media.giphy.com', 'i.redd.it', 'i.reddituploads.com',
                  'pbs.twimg.com', 'instagram.com']
        tweets = ['twitter.com']
        videos = ['youtube.com', 'streamable.com', 'youtu.be', 'vimeo.com', 'vid.me', 'v.redd.it']
        for submission in get_submissions(self.type_, self.name, self.sort, 100):
            domain = submission.domain
            if domain.startswith('self.'):
                self.domains['Self Text'] = self.domains.get('Self Text', 0) + 1
            elif domain in images:
                self.domains['Images'] = self.domains.get('Images', 0) + 1
            elif domain in tweets:
                self.domains['Tweets'] = self.domains.get('Tweets', 0) + 1
            elif domain in videos:
                self.domains['Videos'] = self.domains.get('Videos', 0) + 1
            else:
                self.domains['Links'] = self.domains.get('Links', 0) + 1


def generate_word_chain(corpus):
    word_chain = {}
    for comment in corpus:
        comment = clean_comment(comment)
        if not comment:
            continue
        for i, word in enumerate(comment):
            try:
                first, second, third = comment[i], comment[i + 1], comment[i + 2]
            except IndexError:
                break
            key = (first, second)
            if key not in word_chain:
                word_chain[key] = []
            word_chain[key].append(third)
    return word_chain


# Algorithm from www.onthelambda.com
def generate_markov_chain(start_words, word_chain):
    if not start_words:
        return None
    first, second = random.choice(start_words)

    sentence = [first, second]
    max_len = 0
    while max_len < 50:
        try:
            third = random.choice(word_chain[(first, second)])
        except KeyError:
            break
        sentence.append(third)
        if third[-1] in ['!', '.', '?']:
            break
        first, second = second, third
        max_len += 1

    return ' '.join(sentence)


def clean_comment(comment):
    if comment in ('[removed]', '[deleted]'):
        return
    cleaned = []
    for word in comment.split():
        if URL_RE.search(word) or REFERENCE_RE.search(word):
            # Word is url or reference to user/subreddit
            continue
        for token in MARKOV_RE.findall(word):
            if token == 'nbsp':
                continue
            cleaned.append(token)
    return cleaned


def get_tokens(comments):
    for comment in comments:
        if comment in ('[removed]', '[deleted]'):
            continue
        for word in comment.split():
            if URL_RE.search(word) or REFERENCE_RE.search(word):
                # Word is url or reference to user/subreddit
                continue
            else:
                for token in TOKEN_RE.findall(word):
                    if token.endswith("'s"):  # Fix possessives
                        token = token[:-2]
                    if token.lower() in WHITELIST or token.isdecimal() or token == 'nbsp':  # Ignore word
                        continue
                    yield token.lower()


def create_iterable_by_sort(obj, sort, limit):
    if sort == 'top':
        return obj.top(limit=limit)
    elif sort == 'new':
        return obj.new(limit=limit)
    elif sort == 'controversial':
        return obj.controversial(limit=limit)
    elif sort == 'hot':
        return obj.hot(limit=limit)


def get_submissions(type_, name, sort, limit):
    if type_ == 'User':
        return create_iterable_by_sort(REDDIT.redditor(name).submissions, sort, limit)
    else:
        return create_iterable_by_sort(REDDIT.subreddit(name), sort, limit)


def get_corpus_from_user(user, sort='top'):
    comments = []
    user = REDDIT.redditor(user)
    for submission in create_iterable_by_sort(user.submissions, sort, 200):
        comments.extend([submission.title, submission.selftext])
    for comment in create_iterable_by_sort(user.comments, sort, 500):
        comments.append(comment.body)
    with open('log.txt', 'a+') as file:
        file.write('Number of comments and submissions analyzed: {}\n'.format(len(comments)))
    return comments


def get_corpus_from_submission(submission, comment_sort):
    submission.comment_sort = comment_sort
    submission.comments.replace_more(limit=0)
    flat_comments = submission.comments.list()
    comments = [comm.body for comm in flat_comments]
    comments.extend([submission.title, submission.selftext])
    return comments


def get_corpus_from_subreddit(subreddit, sort, comment_sort, limit):
    comments = []
    for submission in create_iterable_by_sort(REDDIT.subreddit(subreddit), sort, limit):
        comments.extend(get_corpus_from_submission(submission, comment_sort))
    with open('log.txt', 'a+') as file:
        file.write('Number of submissions analyzed: {}\nNumber of comments analyzed: {}\n'.format(limit, len(comments)))
    return comments


if __name__ == '__main__':
    open('log.txt', 'w+').truncate()
    root = tk.Tk()
    window = Window(root)
    root.mainloop()
