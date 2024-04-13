import chess


def translate_color(string):
    if string == "white":
        return "bianco"
    else:
        return "nero"


def get_color_to_move(pgn):
    return "white" if is_white_to_move(pgn) else "black"


def is_white_to_move(pgn):
    return len(pgn.split(' ')) % 2 == 0


def convert_uci_to_human(uci_moves):
    human_moves = ""
    for uci_move in uci_moves:
        move = chess.Move.from_uci(uci_move)
        human_moves += str(move) + " "
    return human_moves
