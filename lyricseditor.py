import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from mutagen import File
from mutagen.flac import FLACNoHeaderError, error # Keep for specific FLAC error handling, though general Exception is also used
from mutagen.mp3 import MP3
from mutagen.id3 import USLT, ID3NoHeaderError # For handling Unsynchronised Lyrics/Text (USLT) frames in MP3s

class MusicLyricsEditor(tk.Tk):
    """
    A Tkinter application for editing lyrics metadata in various music files (FLAC, MP3, etc.).
    Supports keyboard shortcuts for common actions and improved error handling.
    """
    def __init__(self):
        super().__init__()
        self.title("Music Lyrics Editor")
        self.geometry("1000x900") # Increased window height for better button visibility

        self.music_files = []
        self.sorted_files = []
        self.current_file_index = -1
        
        self.create_widgets()
        self.bind_shortcuts() # Bind keyboard shortcuts

    def create_widgets(self):
        """
        Creates and lays out the widgets for the application's user interface.
        """
        # Top frame: File browsing button and file list
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.browse_button = tk.Button(top_frame, text="Select Music Folder (Ctrl+O)", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT)

        self.file_list_frame = tk.Frame(self)
        self.file_list_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        self.file_list_label = tk.Label(self.file_list_frame, text="File List")
        self.file_list_label.pack(anchor="w")

        self.file_listbox = tk.Listbox(self.file_list_frame, height=15, font=("Helvetica", 10))
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        scrollbar = tk.Scrollbar(self.file_list_frame, orient="vertical")
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # Lyrics display and input area
        lyrics_frame = tk.Frame(self)
        lyrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        lyrics_label = tk.Label(lyrics_frame, text="Lyrics:")
        lyrics_label.pack(anchor="w")
        
        self.lyrics_text = tk.Text(lyrics_frame, wrap=tk.WORD, font=("Helvetica", 12))
        self.lyrics_text.pack(expand=True, fill=tk.BOTH)
        
        # Bottom frame: Save and navigation buttons
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        self.save_button = tk.Button(bottom_frame, text="Save Lyrics (Ctrl+S)", command=self.save_lyrics, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.clear_button = tk.Button(bottom_frame, text="Clear Lyrics (Ctrl+L)", command=self.clear_lyrics, state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.prev_button = tk.Button(bottom_frame, text="Previous File (Ctrl+P)", command=self.show_previous_file, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 5))

        self.next_button = tk.Button(bottom_frame, text="Next File (Ctrl+N)", command=self.show_next_file, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    def bind_shortcuts(self):
        """
        Binds keyboard shortcuts to various application functions.
        Handles both Windows/Linux (Control) and macOS (Command) key presses.
        """
        self.bind("<Control-s>", lambda event: self.save_lyrics())
        self.bind("<Command-s>", lambda event: self.save_lyrics()) # For macOS
        
        self.bind("<Control-l>", lambda event: self.clear_lyrics())
        self.bind("<Command-l>", lambda event: self.clear_lyrics()) # For macOS

        self.bind("<Control-n>", lambda event: self.show_next_file())
        self.bind("<Command-n>", lambda event: self.show_next_file()) # For macOS

        self.bind("<Control-p>", lambda event: self.show_previous_file())
        self.bind("<Command-p>", lambda event: self.show_previous_file()) # For macOS

        self.bind("<Control-o>", lambda event: self.browse_folder())
        self.bind("<Command-o>", lambda event: self.browse_folder()) # For macOS


    def browse_folder(self):
        """
        Prompts the user to select a folder, finds supported audio files, and sorts them.
        """
        directory = filedialog.askdirectory()
        if directory:
            # List of supported audio file extensions (case-insensitive)
            supported_extensions = ('.flac', '.mp3', '.m4a', '.ogg', '.wav') 
            self.music_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(supported_extensions)]
            
            if not self.music_files:
                messagebox.showinfo("Info", "No supported audio files found in the selected folder.")
                return

            self.sort_files()
            self.update_listbox()
            
    def sort_files(self):
        """
        Sorts the list of music files by artist (A-Z), album year (oldest first), 
        album title (A-Z), and then track number (1 onwards).
        Handles different metadata structures for various file types.
        """
        def get_sort_key(file_path):
            try:
                audio = File(file_path)
                if audio is None: 
                    # If mutagen cannot parse, return default sort key
                    return ('zzzzzz', 9999, 'zzzzzz', 9999)

                artist = audio.get('artist', [''])[0].lower() if 'artist' in audio else 'zzzzzz'
                album = audio.get('album', [''])[0].lower() if 'album' in audio else 'zzzzzz'
                
                date_str = audio.get('date', ['9999'])[0] if 'date' in audio else '9999'
                try:
                    album_year = int(date_str[:4]) 
                except (ValueError, IndexError):
                    album_year = 9999 

                tracknumber_str = audio.get('tracknumber', ['0'])[0] if 'tracknumber' in audio else '0'
                try:
                    tracknumber = int(tracknumber_str.split('/')[0]) if '/' in tracknumber_str else int(tracknumber_str)
                except (ValueError, IndexError):
                    tracknumber = 9999

                return (artist, album_year, album, tracknumber)
            except (FLACNoHeaderError, ID3NoHeaderError, error, ValueError, Exception) as e:
                # Catch specific mutagen errors and general exceptions during metadata reading
                print(f"Error reading metadata for sorting {file_path}: {e}")
                return ('zzzzzz', 9999, 'zzzzzz', 9999) # Return default sort key on error

        self.sorted_files = sorted(self.music_files, key=get_sort_key)

    def update_listbox(self):
        """
        Displays the sorted list of files in the GUI Listbox.
        """
        self.file_listbox.delete(0, tk.END)
        for file_path in self.sorted_files:
            try:
                audio = File(file_path)
                if audio is None:
                    display_name = os.path.basename(file_path) + " (Unsupported/Corrupt)"
                else:
                    artist = audio.get('artist', ['(Unknown Artist)'])[0]
                    album = audio.get('album', ['(Unknown Album)'])[0]
                    title = audio.get('title', ['(Unknown Title)'])[0]
                    
                    date_str = audio.get('date', [''])[0]
                    album_year = date_str[:4] if date_str else '?'
                    
                    tracknumber_str = audio.get('tracknumber', [''])[0]
                    
                    # Format for display in the file list
                    display_name = f"{artist} | {album_year} {album} | Track {tracknumber_str}. {title}"
            except Exception as e: 
                print(f"Error getting display info for {file_path}: {e}")
                display_name = os.path.basename(file_path) + " (Error reading metadata)"
            self.file_listbox.insert(tk.END, display_name)
        
        # Enable buttons after files are loaded
        self.save_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)

        if self.sorted_files:
            self.file_listbox.select_set(0) # Select the first file
            self.on_file_select(None) # Load its lyrics

    def on_file_select(self, event):
        """
        Displays lyrics when a file is selected from the Listbox.
        """
        try:
            selection = self.file_listbox.curselection()
            if selection:
                self.current_file_index = selection[0]
                self.update_ui()
        except IndexError:
            # This can happen if the listbox is empty or selection is cleared
            pass 
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during file selection: {e}")
            
    def update_ui(self):
        """
        Updates the lyrics display area based on the currently selected file.
        Handles different lyric tag keys for various file types.
        """
        if self.current_file_index == -1 or not self.sorted_files:
            self.lyrics_text.delete("1.0", tk.END) # Clear text if no file is selected
            return

        file_path = self.sorted_files[self.current_file_index]
        current_lyrics = ""
        try:
            audio = File(file_path)
            
            if audio is None: 
                messagebox.showwarning("Warning", f"Unsupported or corrupt file: '{os.path.basename(file_path)}'. Cannot read lyrics.")
                self.lyrics_text.delete("1.0", tk.END)
                return
                
            # Get the correct tag key for lyrics based on file type
            if isinstance(audio, MP3) and audio.tags:
                lyrics_tag = audio.tags.get('USLT::eng', None)
                if lyrics_tag:
                    current_lyrics = lyrics_tag.text[0] if lyrics_tag.text else ""
            else: # Fallback to 'lyrics' for most other formats (e.g., FLAC, OGG Vorbis)
                current_lyrics = audio.get('lyrics', [''])[0]
                
        except (FLACNoHeaderError, ID3NoHeaderError, error, ValueError) as e:
            messagebox.showwarning("Warning", f"Error reading lyrics from '{os.path.basename(file_path)}': {e}")
            current_lyrics = ""
        except Exception as e: 
            messagebox.showerror("Error", f"An unexpected error occurred while reading lyrics: {e}")
            current_lyrics = ""
        
        self.lyrics_text.delete("1.0", tk.END) 
        self.lyrics_text.insert("1.0", current_lyrics) 
    
    def save_lyrics(self):
        """
        Saves the current lyrics to the selected file's metadata.
        Handles different tag writing methods for various file types.
        """
        if self.current_file_index == -1 or not self.sorted_files:
            messagebox.showwarning("Warning", "No file selected to save lyrics.")
            return

        file_path = self.sorted_files[self.current_file_index]
        new_lyrics = self.lyrics_text.get("1.0", tk.END).strip()

        try:
            # Check if file exists and is writable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            if not os.access(file_path, os.W_OK):
                raise PermissionError(f"Permission denied to write to file: {file_path}")

            audio = File(file_path)
            if audio is None:
                messagebox.showerror("Error", f"Unsupported or corrupt file: '{os.path.basename(file_path)}'. Cannot save lyrics.")
                return
            
            if isinstance(audio, MP3):
                if not audio.tags:
                    audio.add_tags() # Add ID3 tags if none exist
                audio.tags.set(USLT(encoding=3, lang='eng', desc='', text=new_lyrics))
            else:
                audio['lyrics'] = [new_lyrics]
                
            audio.save() 
            messagebox.showinfo("Success", f"Lyrics successfully saved to '{os.path.basename(file_path)}'.")
        except (FileNotFoundError, PermissionError) as e:
            messagebox.showerror("File Error", f"Cannot save lyrics to '{os.path.basename(file_path)}': {e}")
        except (FLACNoHeaderError, ID3NoHeaderError, error, ValueError) as e:
            messagebox.showerror("Metadata Error", f"Error saving lyrics to '{os.path.basename(file_path)}' due to metadata issues: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while saving lyrics: {e}")

    def clear_lyrics(self):
        """
        Clears the lyrics editing area.
        """
        self.lyrics_text.delete("1.0", tk.END)
        messagebox.showinfo("Cleared", "Lyrics editing area has been cleared.")

    def show_next_file(self):
        """
        Moves to the next file in the sorted list.
        """
        if self.current_file_index < len(self.sorted_files) - 1:
            self.file_listbox.select_clear(self.current_file_index)
            self.current_file_index += 1
            self.file_listbox.select_set(self.current_file_index)
            self.file_listbox.see(self.current_file_index) 
            self.update_ui()
        else:
            messagebox.showinfo("Info", "This is the last file in the list.")

    def show_previous_file(self):
        """
        Moves to the previous file in the sorted list.
        """
        if self.current_file_index > 0:
            self.file_listbox.select_clear(self.current_file_index)
            self.current_file_index -= 1
            self.file_listbox.select_set(self.current_file_index)
            self.file_listbox.see(self.current_file_index) 
            self.update_ui()
        else:
            messagebox.showinfo("Info", "This is the first file in the list.")
    
if __name__ == "__main__":
    app = MusicLyricsEditor()
    app.mainloop()
