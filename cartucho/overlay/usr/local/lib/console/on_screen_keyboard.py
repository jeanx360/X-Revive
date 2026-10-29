"""Physical typing and controller keyboard share one input model."""
import string


class Keyboard:
    def __init__(self):self.text='';self.upper=False;self.symbols=False;self.row=0;self.col=0
    def rows(self):
        if self.symbols:
            chars=list(string.punctuation+'áàâãéêíóôõúüç')
            rows=[chars[i:i+9] for i in range(0,len(chars),9)]
        else:rows=[list(s) for s in ('1234567890','qwertyuiop','asdfghjkl','zxcvbnm')]
        if self.upper:rows=[[c.upper() for c in row] for row in rows]
        return rows+[['abc' if self.upper else 'ABC','Letras' if self.symbols else 'Símbolos','Espaço','Apagar','Conectar','Cancelar']]
    def move(self,dx=0,dy=0):
        rows=self.rows();self.row=(self.row+dy)%len(rows)
        self.col=(self.col+dx)%len(rows[self.row]) if dx else min(self.col,len(rows[self.row])-1)
    def insert(self,text):self.text+=''.join(c for c in text if c.isprintable())[:max(0,256-len(self.text))]
    def erase(self):self.text=self.text[:-1]
    def clear(self):self.text=''
    def choose(self):
        value=self.rows()[self.row][self.col]
        if value in ('Conectar','Cancelar'):return value
        if value=='Apagar':self.erase()
        elif value=='Espaço':self.insert(' ')
        elif value in ('ABC','abc'):self.upper=not self.upper
        elif value in ('Símbolos','Letras'):
            self.symbols=not self.symbols;self.row=len(self.rows())-1
        else:self.insert(value)
        return None
