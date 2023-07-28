# -*- coding: utf-8 -*-
"""Time Series Music Generation.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XQiDakUozsDA7psZg7Bkwak3ZbaB33gQ

# Setup

[LSTM Music Generation Tutorial Series](https://youtube.com/playlist?list=PL-wATfeyAMNr0KMutwtbeDCmpwvtul-Xz)
"""

# !pip install music21
# !pip install numpy
# !pip install tensorflow
# !pip install keras
# !pip install matplotlib
# !apt install fluidsynth #Pip does not work for some reason. Only apt works
# !pip install midi2audio
# !apt-get install musescore3

import os
import json
import music21 as m21
import numpy as np
from tensorflow import keras
from tqdm import tqdm
from midi2audio import FluidSynth
from IPython.display import Audio, display
import gradio as gr

# Data source: http://www.esac-data.org

# MUSIC_GENRE = st.selectbox("Please choose your favorite music genre", (os.listdir("./raw_dataset/deutschl")))   
# KERN_DATASET_PATH = "./raw_dataset/deutschl/" + MUSIC_GENRE

m21.environment.set('musescoreDirectPNGPath', 'C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe')

mapping_path = "./mapping.json"
save_model_path = "./model/cpu_model.h5"
output_midi_path = "./output/melody.mid"
output_audio_path = "./output/melody.wav"
output_image_path = "./output/melody.png"

sequence_length = 64

# durations are expressed in quarter length
acceptable_durations = [
    0.25, # 16th note
    0.5, # 8th note
    0.75,
    1.0, # quarter note
    1.5,
    2, # half note
    3,
    4 # whole note
]

with open(mapping_path, "r") as fp:
    dictionary = json.load(fp)

"""# Generate"""
def convert_songs_to_int(dictionary, songs):
    int_songs = []

    # transform songs string to list
    songs = songs.split()

    # map songs to int
    for symbol in songs:
        int_songs.append(dictionary[symbol])

    return int_songs

def generate_melody(seed, max_sequence_length, song_length, dictionary):
  melody = seed.split()
  seed = convert_songs_to_int(dictionary, seed)
  model = keras.models.load_model(save_model_path)
  """
  Example: seed = [44, 50, 64, 73], max_sequence_length = 3.
  seed[-max_sequence_length:] = seed[-3:] = [50, 64, 73]
  seed.append(67) -> seed = [50, 64, 73, 67]
  seed[-3:] = [64, 73, 67].
  """
  for _ in range(song_length):
    seed = seed[-max_sequence_length:] # Example: seed[-10:] means get the last 10 elements
    onehot_seed = keras.utils.to_categorical(seed, num_classes=len(dictionary)) # one-hot encode the sequences

    onehot_seed = onehot_seed[np.newaxis,...]  # add new axis to onehot_seed matrix. shape = (64, 28) -> (1, 64, 28)
    """ Because Keras expects a batch of samples, so we have to use 3-dimensional array although there is only one 2-dimensional element.
    Example: [[1, 3],[2, 4]] -> [[[1, 3],[2, 4]]]."""

    probabilitites = model.predict(onehot_seed)[0]
    """ Returns a matrix that includes the probability for each music symbol.
    Example: prob = [[0.1, 0.2]] -> Remove new axis with prob[0] = [0.1, 0.2]"""

    max_probability = max(probabilitites) # get the max probability
    max_probability_index = probabilitites.argmax() # get the index of max probability
    predicted_symbol = list(dictionary.keys())[max_probability_index]
    print("Predicted symbol:", predicted_symbol, "\nProbability:", max_probability)

    seed.append(max_probability_index)

    if predicted_symbol == "/":
      break

    melody.append(predicted_symbol)
    # print(melody)

  return melody

def save_melody(melody, midi_path, image_path, step_duration=0.25):
  stream = m21.stream.Stream()

  pre_symbol = None
  step_counter = 1

  for i, symbol in enumerate(melody):

    if symbol == "_" and i + 1 < len(melody):
        step_counter += 1

    else:
      if pre_symbol is not None:
        quarter_length = step_duration * step_counter # Example: ["60", "_", "_", "_"] -> quarter_length = 0.25 * 4 = 1 (a quarter note C)

        if pre_symbol == "r":
          m21_event = m21.note.Rest(quarterLength = quarter_length)
        else:
          m21_event = m21.note.Note(int(pre_symbol), quarterLength = quarter_length)

        stream.append(m21_event)
        step_counter = 1

      pre_symbol = symbol

  stream.write("midi", midi_path)

  print("\nMelody sheet:\n")
  stream.show(fmt="musicxml.png", fp = output_image_path) # fmt: format, fp: file path
  
def play_melody(melody_path, audio_path):
  FluidSynth(sound_font="./sounds/sf2/default-GM.sf2", sample_rate=16000).midi_to_audio(melody_path, audio_path)
  print("\nPlay melody.wav:\n")
  display(Audio(audio_path, rate=16000))

seed = "60 _ _ _ _ 62 _ _ _ _ 64 _ _ _ _ 65 _ _ _ _ 67 _ _ _ _ "

symbol_pitch_list = ["r"]
name_pitch_list = ["Rest"]

for x in dictionary:
    if x.isdigit():
      symbol_pitch_list.append(x) 
      name_pitch_list.append(m21.note.Note(int(x)).nameWithOctave)

def add_symbol(symbol, duration):
    global seed 
    seed += symbol_pitch_list[name_pitch_list.index(symbol)] + " "
    
    duration = float(duration)
    if duration > 0.25:
        for i in range(int(duration/0.25)):
            seed += "_ "

    return seed

def clear_symbol():
    global seed
    seed = ""

def generate_symbol(melody_length):
    melody = generate_melody(seed, sequence_length, melody_length, dictionary)
    print("\nMelody symbols:", melody)

    save_melody(melody, output_midi_path, output_image_path)
    play_melody(output_midi_path, output_audio_path)
    
    return "./output/melody-1.png", output_audio_path

with gr.Blocks(title="Generate music in time series") as music_generation:
  gr.Markdown("""
    # Generate music in time series
    """)
  with gr.Box():
    with gr.Column():
      with gr.Row():
        symbol = gr.Dropdown(choices = name_pitch_list, label="Pitch of note")
        duration = gr.Dropdown(choices = acceptable_durations, label="Duration of note")
      
      seed_melody = gr.Textbox(value = seed, label="Seed melody")

      with gr.Row():
        add_symbol_btn = gr.Button(value="Add symbol")
        clear_symbol_btn = gr.Button(value="Clear symbol")

      add_symbol_btn.click(fn=add_symbol, inputs=[symbol, duration], outputs=seed_melody)
      clear_symbol_btn.click(fn = clear_symbol, outputs=seed_melody)
  
  with gr.Box():
    with gr.Column():
      with gr.Row():
        melody_length = gr.Slider(minimum=100, maximum=1000, label="Melody length")
        generate_btn = gr.Button(value="Generate melody")
      
      with gr.Row():
        melody_image = gr.Image(label="Melody sheet")
        melody_audio = gr.Audio(label="Melody audio")

      generate_btn.click(fn=generate_symbol, inputs=melody_length, outputs=[melody_image, melody_audio])

music_generation.launch()