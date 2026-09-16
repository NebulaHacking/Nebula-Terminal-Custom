class Solution(object):
    def romanToInt(self, s):
        """
        :type s: str
        :rtype: int
        """
    s = input("symbols : ")
    symbols = list(s)
    value_n = 0

    for i in range(len(symbols)):
        # On récupère le caractère à l'index i
        caractere = symbols[i]
        
        if caractere == "I":
            value_n += 1  # Bien utiliser += ici aussi !
        elif caractere == "V":
            value_n += 5
        elif caractere == "X":
            value_n += 10
        elif caractere == "L":
            value_n += 50
        elif caractere == "C":
            value_n += 100
        elif caractere == "D":
            value_n += 500
        elif caractere == "M":
            value_n += 1000

    print(value_n)