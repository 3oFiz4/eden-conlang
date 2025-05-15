import tkinter as tk
from tkinter import messagebox
import json
import re
import argparse
import os, sys
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
import json
# Checking if things working. Test GIT_NVIM

DATA_FILE = os.path.join(os.path.dirname(__file__), "dict.json")
RULE_FILE = os.path.join(os.path.dirname(__file__), "rule.json")
try:
    with open(RULE_FILE, "r", encoding="utf-8") as rf:
        RULESET = json.load(rf)  # now a list of {englishPattern,…} or {edenPattern,…}
except (FileNotFoundError, json.JSONDecodeError):
    RULESET = []

# compile every grammar rule in order
english_rules = []
eden_rules    = []
for r in RULESET:
    if "englishPattern" in r and "englishResult" in r:
        try:
            english_rules.append((re.compile(r["englishPattern"], re.IGNORECASE),
                                  r["englishResult"]))
        except re.error:
            pass
    if "edenPattern" in r and "edenResult" in r:
        try:
            eden_rules.append((re.compile(r["edenPattern"],    re.IGNORECASE),
                               r["edenResult"]))
        except re.error:
            pass
phonetic_to_romanization = {  "a\\": "à", "a^": "â", "a/": "á",  "iv": "ĭ", "i^": "î",  "uv": "ǔ", "u/": "ú",  "e^": "ê", "e\\": "è", "e.": "ė",  "*e_": "ɘ", "*ev": "ɛ", "*e^": "ɨ",  "o/": "ó", "o-": "ō", "o^": "ô",  "td": "ɜ", "dd": "δ","fw": "λ","vw": "ζ","th": "ṫ","dh": "ḋ","sh": "ṡ","zh": "ż","rs": "ς","rz": "ẕ","xhi": "ŝ","zhi": "ẑ","xkh": "x","xgh": "ẋ","xhk": "ӡ","xhg": "ʁ","#": "h","H": "ḣ","nd": "ɴ","nh": "ռ", "rn": "ɳ","ny": "ɲ","ng": "ŋ","wv": "ς","rw": "ɍ","rrn": "ɵ","j": "y","r.": "ŕ","r": "r","l": "l"
                            }
romanization_to_phonetic = {"a\\": "ɑ", "a^": "æ", "a/": "ʌ", "iv": "y", "i^": "ɯ",          "uv": "ʊ", "u/": "ʏ",          "e^": "ø", "e\\": "ɛ", "e.": "ɪ",          "*e_": "ɘ", "*ev": "ə", "*e^": "ə",          "o/": "ɵ", "o-": "ɤ", "o^": "ɔ",
                            "td": "t̪","dd": "d̪","fw": "ɸ","vw": "β","th": "θ","dh": "ð","sh": "ʃ","zh": "ʒ","rs": "ʂ","rz": "ʐ","xhi": "ɕ","zhi": "ʑ","xkh": "x","xgh": "ɣ","xhk": "χ","xhg": "ʁ","#": "ɦ","H": "ɦ","nd": "n̼","nh": "n̥n","rn": "ɳ","ny": "ɲ","ng": "ŋ","wv": "ʋ","rw": "ɹ","rrn": "ɻ","j": "y","r.": "ɾ","r": "r","l": "l"      }

def load(entry):
    target_file=DATA_FILE
    tmp_file = f"~{DATA_FILE}"

    # Use temp file if it exists and is valid
    if os.path.exists(tmp_file):
        try:
            with open(tmp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            target_file = tmp_file  # Write back to temp file
        except json.JSONDecodeError:
            print(f"[ERROR] {tmp_file} exists but contains invalid JSON. Aborting to avoid data loss.")
            return
    else:
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

    data.append(entry)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def process_translations(text, vocab_data):
    """Standalone fn: apply all grammar rules in order, then fallback."""
    def handle_square_bracket(m):
        """
        Rule: fn edenVocab: [<$n>*:*(r(V) & V)] -> r(englishVocab[<$n>*]) & englishVocab[<$n>*]
        Such that (einon = lightning; to struct):
        - [:einon] -> lightning; to struck
        - [einon] -> lightning
        - [2:einon] -> to struck
        - r(V) | Rules applied at V -> r(englishVocab[<$n>*]) | Equivalent rule applied only for englishVocab of V entry
        """
        content = m.group(1).strip()
        # [n:lookup]?
        if ":" in content:
            idx_str, lookup = map(str.strip, content.split(":", 1))
            # try each eden-rule
            for pat, res in eden_rules:
                g = pat.match(lookup)
                if g:
                    base = g.group(1)
                    tgt = next((v for v in vocab_data
                                if v["edenVocab"].lower()==base.lower()), {})
                    parts = [p.strip() for p in tgt.get("englishVocab","").split(";") if p.strip()]
                    try:
                        if idx_str: # [n:V]?
                            eq = parts[int(idx_str)-1]
                        else: # [:V]?
                            eq = '; '.join(parts)
                    except: # ![n:V] & ![:V]
                        eq = parts if idx_str else lookup
                        # a bit of change in here, instead of "#", the input value instead. (check line 173)
                    return res.replace("$1", eq)
            # default index-lookup
            tgt = next((v for v in vocab_data if v["edenVocab"].lower()==lookup.lower()), None)
            if not tgt: return ""
            parts = [p.strip() for p in tgt["englishVocab"].split(";") if p.strip()]
            try: return parts[int(idx_str)-1]
            except: return ""
        # [lookup]
        # try eden-rules
        for pat, res in eden_rules:
            g = pat.match(content)
            if g:
                base = g.group(1)
                tgt = next((v for v in vocab_data
                            if v["edenVocab"].lower()==base.lower()), {})
                parts = [p.strip() for p in tgt.get("englishVocab","").split(";") if p.strip()]
                eq = parts[0] if parts else base # a bit of change in here, instead of "#", the input value instead.
                return res.replace("$1", eq)
        # fallback: n-meaning lookup
        tgt = next((v for v in vocab_data if v["edenVocab"].lower()==content.lower()), None)
        if not tgt: return ""
        parts = [p.strip() for p in tgt["englishVocab"].split(";") if p.strip()]
        return parts[0] if len(parts)==1 else f"({'; '.join(parts)})"

    def handle_parentheses(m):
        """
        Rule: fn englishVocab: ((r(V) & V)) -> r(edenVocab) & edenVocab
        Such that (einon = lightning; to struck):
        - (to struck) -> einon
        - (lightning) -> einon
        - r(V) | Rules applied at V -> r(edenVocab) | Equivalent rule applied only for edenVocab of V entry
        """
        content = m.group(1).strip()
        # try English-rules
        for pat, res in english_rules:
            g = pat.match(content)
            if g:
                grp = g.group(1)
                tgt = next((v for v in vocab_data
                            if any(grp.lower()==p.strip().lower()
                                   for p in v["englishVocab"].split(";"))),
                           {})
                ed = tgt.get("edenVocab", "#")
                return res.replace("$1", ed)
        # fallback reverse lookup
        for v in reversed(vocab_data):
            parts = [p.strip().lower() for p in v["englishVocab"].split(";") if p.strip()]
            if any(content.lower()==p or content.lower() in p for p in parts):
                return v["edenVocab"]
        return ""

    out = re.sub(r"\[([^]]*)\]", handle_square_bracket, text)
    out = re.sub(r"\(([^)]*)\)", handle_parentheses, out)
    return out
class VocabManager:
    def __init__(self, master):
        self.master = master
        self.master.title("Vocab Manager")

        # Load existing vocab data
        self.load_vocab_data()

        # Create input fields
        self.create_input_fields()

        # Create buttons
        self.create_buttons()
    

    def load_vocab_data(self):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                self.vocab_data = json.load(file)
                # Validate each vocab entry
                self.vocab_data = [vocab for vocab in self.vocab_data if self.validate_vocab(vocab)]
        except (FileNotFoundError, json.JSONDecodeError):
            self.vocab_data = []


    def validate_vocab(self, vocab):
        # Ensure all required fields are present and not empty
        required_fields = ["edenVocab", "edenRomanization", "edenPhonetic", "englishVocab", "semanticAtom", "note"]
        return all(field in vocab and vocab[field] for field in required_fields)

    def create_input_fields(self):
        self.entries = {}
        self.info_labels = {}
        fields = ["edenVocab", "edenRomanization", "edenPhonetic", "englishVocab", "semanticAtom", "note", "Translate"]
        for idx, field in enumerate(fields):
            label = tk.Label(self.master, text=field)
            label.grid(row=idx, column=0, padx=10, pady=5)
            
            if field == "note":
                # Create Text widget with scrollbar for note field
                entry = tk.Text(self.master, height=3, wrap=tk.WORD)
                scroll = tk.Scrollbar(self.master, command=entry.yview)
                entry.configure(yscrollcommand=scroll.set)
                entry.grid(row=idx, column=1, padx=10, pady=5)
                scroll.grid(row=idx, column=2, sticky='nsew')
            else:
                entry = tk.Entry(self.master)
                entry.grid(row=idx, column=1, padx=10, pady=5)
            
            entry.bind("<KeyRelease>", self.live_check_for_duplicates)
            if field in ["edenRomanization", "edenPhonetic"]:
                entry.bind("<KeyRelease>", self.convert_romanization_phonetic)
            
            if field == "Translate":    
                entry.bind("<KeyRelease>", self.translate_text)
                # Add label for cleaned translation text
                self.cleaned_translate_label = tk.Label(self.master, text="", fg="green")
                self.cleaned_translate_label.grid(row=idx, column=2, padx=10, pady=5)

            self.entries[field] = entry
            info_label = tk.Label(self.master, text="", fg="blue")
            info_label.grid(row=idx, column=3 if field == "note" else 2, padx=10, pady=5)
            self.info_labels[field] = info_label

    def create_buttons(self):
        self.add_button = tk.Button(self.master, text="Add", command=self.add_vocab)
        self.add_button.grid(row=7, column=0, padx=10, pady=10)

        remove_button = tk.Button(self.master, text="Remove", command=self.remove_vocab)
        remove_button.grid(row=7, column=1, padx=10, pady=10)

    def add_vocab(self):
        new_vocab = {field: self.entries[field].get("1.0", tk.END).strip() if field == "note" else self.entries[field].get() 
                    for field in self.entries}
        
        # Process translation patterns
        translate_text = new_vocab.get("Translate", "")
        processed_text = self.process_translations(translate_text)
        
        if processed_text:
            new_vocab["note"] = processed_text.replace('\n', '\\n')
            self.entries["note"].delete("1.0", tk.END)
            self.entries["note"].insert(tk.END, new_vocab["note"])
        
        load(new_vocab)

        

    def process_translations(self, text):
        """GUI-specific wrapper for standalone processor"""
        return process_translations(text, self.vocab_data)

    def translate_text(self, event=None):
        """Live-update the note field from the Translate entry."""
        txt = self.entries["Translate"].get()
        result = self.process_translations(txt)
        
        # Update cleaned translation display
        cleaned_text = re.sub(r'[()\[\]]', '', txt)
        self.cleaned_translate_label.config(text=cleaned_text)
        
        # Update note field
        self.entries["note"].delete("1.0", tk.END)
        self.entries["note"].insert(tk.END, result)

    def _handle_square_bracket(self, content):
        content = content.strip()
        if ':' in content:
            index_str, lookup = map(str.strip, content.split(':', 1))
            lookup_lower = lookup.lower()
            target = next((v for v in self.vocab_data
                           if v['edenVocab'].strip().lower() == lookup_lower), None)
            if not target:
                return ''
            parts = [p.strip() for p in target['englishVocab'].split(';') if p.strip()]
            try:
                idx = int(index_str) - 1
                return parts[idx] if 0 <= idx < len(parts) else ''
            except ValueError:
                return ''
        lookup_lower = content.lower()
        target = next((v for v in self.vocab_data
                       if v['edenVocab'].strip().lower() == lookup_lower), None)
        if not target:
            return ''
        parts = [p.strip() for p in target['englishVocab'].split(';') if p.strip()]
        if len(parts) == 1:
            return parts[0]
        return f"({'; '.join(parts)})"

    def _handle_parentheses(self, content):
        lookup_lower = content.strip().lower()
        for v in reversed(self.vocab_data):
            english_parts = [p.strip().lower() for p in v['englishVocab'].split(';') if p.strip()]
            if any(lookup_lower == part or lookup_lower in part for part in english_parts):
                return v['edenVocab']
        return ''

    def live_check_for_duplicates(self, event=None):
        new_vocab = {field: self.entries[field].get("1.0", tk.END).strip() if isinstance(self.entries[field], tk.Text) 
                    else self.entries[field].get() for field in self.entries}
        duplicate_found = False

        for field in self.entries:
            self.entries[field].config(bg='white')
            self.info_labels[field].config(text="")

        for idx, vocab in enumerate(self.vocab_data):
            for field, value in new_vocab.items():
                if value:
                    if field == "semanticAtom":
                        if value == "$":
                            eden_vocab = self.entries["edenVocab"].get("1.0", tk.END).strip() if isinstance(self.entries["edenVocab"], tk.Text) \
                                        else self.entries["edenVocab"].get().strip()
                            if eden_vocab:
                                components = []
                                seen_substrings = set()
                                for v in sorted(self.vocab_data, 
                                             key=lambda x: len(x["edenVocab"]), 
                                             reverse=True):
                                    ev = v["edenVocab"].strip()
                                    if ev and ev.lower() != eden_vocab.lower():
                                        if re.search(rf'\b{re.escape(ev)}\b', eden_vocab, re.IGNORECASE):
                                            if ev.lower() not in seen_substrings:
                                                components.append(v["englishVocab"])
                                                seen_substrings.add(ev.lower())
                                if len(components) >= 2:
                                    new_semantic = " + ".join(components)
                                    self.entries["semanticAtom"].delete(0, tk.END)
                                    self.entries["semanticAtom"].insert(0, new_semantic)
                                    self.entries["semanticAtom"].config(bg='lightgreen')
                                    new_vocab["semanticAtom"] = new_semantic
                                    duplicate_found = True  # Prevent adding until resolved
                                    continue  # Skip further checks for this field

                        if value.lower() == vocab[field].lower():
                            self.entries[field].config(bg='red')
                            duplicate_found = True
                    else:
                        if field in vocab:
                            if value.lower() == vocab[field].lower():
                                self.entries[field].config(bg='red')
                                duplicate_found = True
                            else:
                                pattern = r'\b' + re.escape(value) + r'\b'
                                if re.search(pattern, vocab[field], re.IGNORECASE):
                                   """There seeems to be a bug here?
                                    (1) For rule that explicitly stated the NON-Capital vowe that has no capital equilvalent, an error happen in this line. Not sure why.
                                   """
                                   self.entries[field].config(bg='yellow')
                                   json_line_number = 1 + sum(len(json.dumps(self.vocab_data[i], indent=2).splitlines()) for i in range(idx))
                                   self.info_labels[field].config(text=f"At Line {json_line_number}")
                                   duplicate_found = True
                        else:
                            self.entries[field].config(bg='white')

        self.add_button.config(state=tk.DISABLED if duplicate_found else tk.NORMAL)

    def remove_vocab(self):
        eden_vocab = self.entries["edenVocab"].get()
        if eden_vocab:
            self.vocab_data = [vocab for vocab in self.vocab_data if vocab["edenVocab"] != eden_vocab]
            self.save_vocab_data()
            messagebox.showinfo("Success", f"Vocab '{eden_vocab}' removed successfully!")
        else:
            messagebox.showwarning("Input Error", "Please enter the edenVocab to remove.")

    def save_vocab_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(self.vocab_data, file, indent=2, ensure_ascii=False)
        

    def convert_romanization_phonetic(self, event=None):
        modified_field = event.widget if event else None
        
        # Only process when focus is lost from a field
        if event and event.type == '9':  # FocusOut event
            if modified_field == self.entries["edenRomanization"]:
                eden_romanization = self.entries["edenRomanization"].get()
                eden_phonetic = eden_romanization
                for shortcut, phonetic in romanization_to_phonetic.items():
                    eden_phonetic = re.sub(r'~' + re.escape(shortcut), phonetic, eden_phonetic)
                    eden_romanization = re.sub(r'~' + re.escape(shortcut), phonetic_to_romanization[shortcut], eden_romanization)
                self.entries["edenPhonetic"].delete(0, tk.END)
                self.entries["edenPhonetic"].insert(0, eden_phonetic)
                self.entries["edenRomanization"].delete(0, tk.END)
                self.entries["edenRomanization"].insert(0, eden_romanization)

            elif modified_field == self.entries["edenPhonetic"]:
                eden_phonetic = self.entries["edenPhonetic"].get()
                eden_romanization = eden_phonetic
                for phonetic, shortcut in phonetic_to_romanization.items():
                    eden_romanization = re.sub(r'~' + re.escape(phonetic), shortcut, eden_romanization)
                    eden_phonetic = re.sub(r'~' + re.escape(phonetic), romanization_to_phonetic[phonetic], eden_phonetic)
                self.entries["edenRomanization"].delete(0, tk.END)
                self.entries["edenRomanization"].insert(0, eden_romanization)
                self.entries["edenPhonetic"].delete(0, tk.END)
                self.entries["edenPhonetic"].insert(0, eden_phonetic)
        else:
            eden_romanization = self.entries["edenRomanization"].get()
            eden_phonetic = self.entries["edenPhonetic"].get()
            for shortcut, phonetic in romanization_to_phonetic.items():
                eden_phonetic = re.sub(r'~' + re.escape(shortcut), phonetic, eden_phonetic)
                eden_romanization = re.sub(r'~' + re.escape(shortcut), phonetic_to_romanization[shortcut], eden_romanization)
            for phonetic, shortcut in phonetic_to_romanization.items():
                eden_romanization = re.sub(r'~' + re.escape(phonetic), shortcut, eden_romanization)
                eden_phonetic = re.sub(r'~' + re.escape(phonetic), romanization_to_phonetic[phonetic], eden_phonetic)
            self.entries["edenPhonetic"].delete(0, tk.END)
            self.entries["edenPhonetic"].insert(0, eden_phonetic)
            self.entries["edenRomanization"].delete(0, tk.END)
            self.entries["edenRomanization"].insert(0, eden_romanization)

def add_vocab_cli():
    def conv(text):
        eden_r = text
        eden_p = text
        for sc, ph in romanization_to_phonetic.items():
            eden_p = re.sub(r'~' + re.escape(sc), ph, eden_p)
            eden_r = re.sub(r'~' + re.escape(sc), phonetic_to_romanization[sc], eden_r)
        for ph, sc in phonetic_to_romanization.items():
            eden_r = re.sub(r'~' + re.escape(ph), sc, eden_r)
            eden_p = re.sub(r'~' + re.escape(ph), romanization_to_phonetic[ph], eden_p)
        return eden_r, eden_p
    parser = argparse.ArgumentParser(description="Add a vocab entry from the command line")
    parser.add_argument("edenShortcut", help="Shortcut for edenVocab (use ~coding for diacritics)")
    parser.add_argument("englishVocab", help="English translation")
    parser.add_argument("semanticAtom", nargs="?", default="", help='Semantic atom or "-" to skip')
    parser.add_argument("note", nargs="*", default=[], help='Note text or "-" for none')
    args = parser.parse_args()

    sem = "" if args.semanticAtom == "-" else args.semanticAtom
    note = "" if args.note == ["-"] else " ".join(args.note)

    eden_r, eden_p = conv(args.edenShortcut)
    new_entry = {
        "edenVocab": eden_r,
        "edenRomanization": eden_r,
        "edenPhonetic": eden_p,
        "englishVocab": args.englishVocab,
        "semanticAtom": sem,
        "note": note
    }

    

    console = Console()    # console.print(panel)
    # Check for existing entries and flag within the panel
    flagged_fields = {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = []

    for key, value in new_entry.items():
        if not value:
            continue  # Skip empty values

        for existing_entry in existing_data:
            for existing_key, existing_value in existing_entry.items():
                if not existing_value:
                    continue  # Skip empty values
                if str(existing_value) in value:
                    flagged_fields[key] = "#00ff00 bold"
                    # Check if value matches existing_value exactly (case insensitive)
                    if value.lower() == str(existing_value).lower():
                         flagged_fields[key] = "red bold"
                    break  # Only flag once per existing entry
            else:
                continue
            break  # Only flag once per field

    # Modify new_entry to include flags
    formatted_entry = {}
    for key, value in new_entry.items():
        if key in flagged_fields:
            formatted_entry[key] = f"[{flagged_fields[key]}]{value}[/]"
        else:
            formatted_entry[key] = value

    

    panel_content = "\n".join(f"{key}: {value}" for key, value in formatted_entry.items())
    panel = Panel(panel_content, title="Entry", border_style="blue")
    console.print(panel)

    inp = console.input("[#ffff00]y? (y):[/][#00ff00] ")
    if inp.lower() == "y":
        load(new_entry)
        console.print("[green][+] <= Added[/green]")
    else:
        console.print("[red][-] => Denied[/red]")
    
    
def search_vocab(search_term):
    """Search dict.json for entries matching the search term using regex"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No data found or invalid JSON")
        return

    # Parse search term in format "field:value"
    if ":" in search_term:
        field, value = search_term.split(":", 1)
        field = field.strip()
        value = value.strip()
    else:
        field = None
        value = search_term.strip()

    matches = []
    for entry in data:
        if field:  # Search specific field
            if field in entry and re.search(value, str(entry[field]), re.IGNORECASE):
                matches.append(entry)
        else:  # Search all fields
            for key, val in entry.items():
                if re.search(value, str(val), re.IGNORECASE):
                    matches.append(entry)
                    break

    if matches:
        console = Console()
        for i, match in enumerate(matches, 1):
            formatted_entry = {}
            for key, val in match.items():
                # Highlight the search term in cyan
                if re.search(value, str(val), re.IGNORECASE):
                    highlighted_val = re.sub(
                        f"({re.escape(value)})", 
                        r"[cyan]\1[/]", 
                        str(val), 
                        flags=re.IGNORECASE
                    )
                    # Highlight the key in yellow if it's the specified field
                    if field and key == field:
                        formatted_entry[f"[yellow]{key}[/]"] = highlighted_val
                    else:
                        formatted_entry[key] = highlighted_val
                else:
                    if field and key == field:
                        formatted_entry[f"[yellow]{key}[/]"] = val
                    else:
                        formatted_entry[key] = val

            panel_content = "\n".join(f"{key}: {value}" for key, value in formatted_entry.items())
            panel = Panel(panel_content, title=f"Match {i}", border_style="green")
            console.print(panel)
    else:
        print("No matches found")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-s", "--search") and len(sys.argv) > 2:
            search_vocab(sys.argv[2])
        elif sys.argv[1] in ("-t", "--translate") and len(sys.argv) > 2:
            # Load vocab data for translation processing
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                vocab_data = json.load(f)
            # Process and print the translation
            result = process_translations(sys.argv[2], vocab_data)
            print(result)
        else:
            add_vocab_cli()
    else:
        root = tk.Tk()
        app = VocabManager(root)
        root.mainloop()
