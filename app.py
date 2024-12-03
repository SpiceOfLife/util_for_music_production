from flask import Flask, render_template, request, jsonify
from mido import MidiFile, MidiTrack, Message, MetaMessage
from io import BytesIO

app = Flask(__name__)

# Function to parse chord name into root note and chord type
def parse_chord(chord_name):
    note_mapping = {
        'C': 48, 'C#': 49, 'Db': 49,
        'D': 50, 'D#': 51, 'Eb': 51,
        'E': 52,
        'F': 53, 'F#': 54, 'Gb': 54,
        'G': 55, 'G#': 56, 'Ab': 56,
        'A': 57, 'A#': 58, 'Bb': 58,
        'B': 59
    }
    chord_intervals = {
        'maj7': [0, 4, 7, 11],  # Root, Major 3rd, Perfect 5th, Major 7th
        'min7': [0, 3, 7, 10],  # Root, Minor 3rd, Perfect 5th, Minor 7th
        '7': [0, 4, 7, 10],     # Root, Major 3rd, Perfect 5th, Minor 7th (Dominant 7th)
        'm7b5': [0, 3, 6, 10],  # Root, Minor 3rd, Diminished 5th, Minor 7th
        'dim7': [0, 3, 6, 9],   # Root, Minor 3rd, Diminished 5th, Diminished 7th
    }
    for note in note_mapping.keys():
        if chord_name.startswith(note):
            root_note = note_mapping[note]
            chord_type = chord_name[len(note):]  # Extract chord type
            if chord_type in chord_intervals:
                return root_note, chord_type
    raise ValueError(f"Invalid chord name '{chord_name}'")

# Function to generate MIDI data as bytes
def generate_midi(tempo_bpm, progression, voicing, rhythm_pattern):
    # テンポのバリデーション
    try:
        tempo_bpm = int(tempo_bpm)
        if tempo_bpm < 40 or tempo_bpm > 240:
            raise ValueError("Tempo must be between 40 and 240.")
    except ValueError:
        raise ValueError("Tempo must be a valid number between 40 and 240.")

    # コード進行のバリデーション
    if not progression:
        raise ValueError("Chord progression cannot be empty.")
    
    # Voicingのバリデーション
    if not voicing:
        raise ValueError("Voicing cannot be empty.")

    # Rhythm patternのバリデーション
    if rhythm_pattern not in ['1', '2']:
        raise ValueError("Invalid rhythm pattern selected.")

    # Rhythm pattern logic
    pattern = [480, 240, 240, 480] if rhythm_pattern == '1' else [960, 480, 480]
    
    # Create MIDI file in memory
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)

    # Add tempo meta message
    tempo = int(60000000 / int(tempo_bpm))
    track.append(MetaMessage('set_tempo', tempo=tempo))

    # Parse the chord progression
    bars = progression.split('|')
    for bar in bars:
        chords_in_bar = bar.split('-')

        if len(chords_in_bar) == 1:  # One chord per bar
            root_note, chord_type = parse_chord(chords_in_bar[0])
            intervals = [root_note + interval for interval in [0, 4, 7, 11]]  # maj7 intervals
            for beat in pattern:
                for note in intervals:
                    track.append(Message('note_on', note=note, velocity=64, time=0))
                track.append(Message('note_off', note=intervals[0], velocity=64, time=beat))

        elif len(chords_in_bar) == 2:  # Two chords split within a bar
            for i, chord in enumerate(chords_in_bar):
                root_note, chord_type = parse_chord(chord)
                intervals = [root_note + interval for interval in [0, 4, 7, 11]]  # maj7 intervals
                for beat in pattern[:len(pattern)//2]:  # Each chord gets half the pattern
                    for note in intervals:
                        track.append(Message('note_on', note=note, velocity=64, time=0))
                    track.append(Message('note_off', note=intervals[0], velocity=64, time=beat))

    # Save MIDI to a bytes object
    midi_bytes = BytesIO()
    midi.save(file=midi_bytes)
    midi_bytes.seek(0)  # Reset pointer to the start
    return midi_bytes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Get form data
        tempo = request.form['tempo']
        progression = request.form['progression']
        voicing = request.form['voicing']
        rhythm_pattern = request.form['rhythm_pattern']

        # Generate MIDI data
        midi_data = generate_midi(tempo, progression, voicing, rhythm_pattern)
        
        # Convert bytes data to base64-encoded string for safe JSON transport
        midi_data_base64 = midi_data.getvalue().decode("latin1")  # Use latin1 for safe transport
        
        return jsonify({"midi_data": midi_data_base64})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
