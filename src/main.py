from __future__ import annotations

import argparse
import random
import sys
from typing import Optional

from src.AI import AI
from src.Board import Board
from src.InputParser import InputParser
from src.Move import Move
from src.Piece import Piece
import openai

WHITE = True
BLACK = False


def askForPlayerSide() -> bool:
    playerChoiceInput = input(
        'What side would you like to play as [wB]? '
    ).lower()
    if 'w' in playerChoiceInput:
        print('You will play as white')
        return WHITE
    else:
        print('You will play as black')
        return BLACK


def askForDepthOfAI() -> int:
    depthInput = 2
    try:
        depthInput = int(
            input(
                'How deep should the AI look for moves?\n'
                'Warning : values above 3 will be very slow.'
                ' [2]? '
            )
        )
        while depthInput <= 0:
            depthInput = int(
                input(
                    'How deep should the AI look for moves?\n'
                    'Warning : values above 3 will be very slow. '
                    'Your input must be above 0.'
                    ' [2]? '
                )
            )

    except KeyboardInterrupt:
        sys.exit()
    except Exception:
        print('Invalid input, defaulting to 2')
    return depthInput


def printCommandOptions() -> None:
    undoOption = 'u : undo last move'
    printLegalMovesOption = 'l : show all legal moves'
    randomMoveOption = 'r : make a random move'
    printGameMoves = 'gm: moves of current game in PGN format'
    quitOption = 'quit : resign'
    moveOption = 'a3, Nc3, Qxa2, etc : make the move'
    options = [
        undoOption,
        printLegalMovesOption,
        randomMoveOption,
        printGameMoves,
        quitOption,
        moveOption,
        '',
    ]
    print('\n'.join(options))


def printAllLegalMoves(board: Board, parser: InputParser) -> None:
    for move in parser.getLegalMovesWithNotation(
        board.currentSide, short=True
    ):
        print(move.notation)


def getRandomMove(board: Board, parser: InputParser) -> Move:
    legalMoves = board.getAllMovesLegal(board.currentSide)
    randomMove = random.choice(legalMoves)
    randomMove.notation = parser.notationForMove(randomMove)
    return randomMove


def makeMove(move: Move, board: Board) -> None:
    print('Making move : ' + move.notation)
    board.makeMove(move)


def undoLastTwoMoves(board: Board) -> None:
    if len(board.history) >= 2:
        board.undoLastMove()
        board.undoLastMove()


def printBoard(board: Board) -> None:
    print()
    print(board)
    print()
    return "\n" + str(board) + "\n"


def printGameMoves(history: list[tuple[Move, Optional[Piece]]]) -> None:
    counter = 0
    for num, mv in enumerate(history):
        if num % 2 == 0:
            if counter % 6 == 0:
                print()
            print(f'{counter + 1}.', end=' ')
            counter += 1

        print(mv[0].notation, end=' ')
    print()


def game_history(history: list[tuple[Move, Optional[Piece]]]) -> str:
    # list out all the moves in the game
    game_moves = ""
    side = "White"
    for move in history:
        move = move[0]
        if side == "White":
            game_moves += f"White: {move.notation}\n"
            side = "Black"
        else:
            game_moves += f"Black: {move.notation}\n"
            side = "White"
    return game_moves


def startGame(board: Board, playerSide: bool, ai: AI) -> None:
    parser = InputParser(board, playerSide)
    while True:
        if board.isCheckmate():
            if board.currentSide == playerSide:
                print('Checkmate, you lost')
            else:
                print('Checkmate! You won!')
            printGameMoves(board.history)
            return

        if board.isStalemate():
            print('Stalemate')
            printGameMoves(board.history)
            return

        if board.noMatingMaterial():
            print('Draw due to no mating material')
            printGameMoves(board.history)
            return

        if board.currentSide == playerSide:
            # printPointAdvantage(board)
            move = None
            command = input("It's your move." " Type '?' for options. ? ")
            if command.lower() == 'u':
                undoLastTwoMoves(board)
                printBoard(board)
                continue
            elif command.lower() == '?':
                printCommandOptions()
                continue
            elif command.lower() == 'l':
                printAllLegalMoves(board, parser)
                continue
            elif command.lower() == 'gm':
                printGameMoves(board.history)
            elif command.lower() == 'r':
                move = getRandomMove(board, parser)
            elif command.lower() == 'exit' or command.lower() == 'quit':
                return
            try:
                if move is None:
                    move = parser.parse(command)
            except ValueError as error:
                print('%s' % error)
                continue
            makeMove(move, board)
            printBoard(board)

        else:
            print('AI thinking...')
            move = ai.getBestMove()
            move.notation = parser.notationForMove(move)
            makeMove(move, board)
            printBoard(board)


def openAI_move(board, messages):
    prompt = f"You are a chessGPT, a chess AI, and we are playing chess. Here is the game so far:\n{board}\n Game History:\n{game_history(board.history)}\nYou are White and it's your move. Explain a good move and then finally on a newline, reponse with this specific syntax: `MOVE <a move in short algebraic notation (a3, Nc3, Qxa2, etc)>`. IMPORTANT you must use provide the move in the format `MOVE <move>` on the last line or the game will not work."
    messages = [{"role": "system", "content": prompt}] + messages

    # # print conversation
    # for message in messages:
    #     print(message["content"])

    response_text = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0,
        max_tokens=250,
    )["choices"][0]["message"]["content"]
    return response_text

def extract_move(response_text):
    prompt = f"""The following is a player's thoughts about a chess move to make. Please extract the move they decided to make (e.g. a3, Nc3, Qxa2, etc) and return it and NOTHING else.
    
    Examples:

    Input: "I think I should move my queen to a2. MOVE Qxa2"
    Reponse: "Qxa2"
    Input: "My rook is in danger. I should move it to a3. MOVE Ra3"
    Reponse: "Ra3"
    """

    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": "Input: " + response_text}]
    response_text = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        max_tokens=250,
    )["choices"][0]["message"]["content"]
    if "Response: " in response_text:
        response_text = response_text.split("Response: ")[1]
    return response_text

import time
def startGPT4Game(board: Board, playerSide: bool, ai: AI) -> None:
    parser = InputParser(board, playerSide)
    messages = []
    while True:
        # sleep for 1 second to avoid rate limiting
        time.sleep(1)
        if board.isCheckmate():
            if board.currentSide == playerSide:
                print('Checkmate, you lost')
            else:
                print('Checkmate! You won!')
            printGameMoves(board.history)
            return

        if board.isStalemate():
            print('Stalemate')
            printGameMoves(board.history)
            return

        if board.noMatingMaterial():
            print('Draw due to no mating material')
            printGameMoves(board.history)
            return

        if board.currentSide == playerSide:
            # printPointAdvantage(board)
            move = None
            print("ChessGPT is thinking...")
            thought = openAI_move(board, messages)
            time.sleep(1)
            command = extract_move(openAI_move(board, messages))
            print(f"ChessGPT: {thought}")
            if command.lower() == 'u':
                undoLastTwoMoves(board)
                printBoard(board)
                continue
            elif command.lower() == '?':
                printCommandOptions()
                continue
            elif command.lower() == 'l':
                printAllLegalMoves(board, parser)
                continue
            elif command.lower() == 'gm':
                printGameMoves(board.history)
            elif command.lower() == 'r':
                move = getRandomMove(board, parser)
            elif command.lower() == 'exit' or command.lower() == 'quit':
                return
            try:
                if move is None:
                    move = parser.parse(command)
            except ValueError as error:
                print('%s' % error)
                messages = [{"role": "user", "content": f"Note: {error}"}]
                continue
            makeMove(move, board)
            printBoard(board)

        else:
            print('Opponent chess engine thinking...')
            move = ai.getBestMove()
            move.notation = parser.notationForMove(move)
            makeMove(move, board)
            printBoard(board)


def twoPlayerGame(board: Board) -> None:
    parserWhite = InputParser(board, WHITE)
    parserBlack = InputParser(board, BLACK)
    while True:
        printBoard(board)
        if board.isCheckmate():
            print('Checkmate')
            printGameMoves(board.history)
            return

        if board.isStalemate():
            print('Stalemate')
            printGameMoves(board.history)
            return

        if board.noMatingMaterial():
            print('Draw due to no mating material')
            printGameMoves(board.history)
            return

        # printPointAdvantage(board)
        if board.currentSide == WHITE:
            parser = parserWhite
        else:
            parser = parserBlack
        command = input(
            "It's your move, {}.".format(board.currentSideRep())
            + " Type '?' for options. ? "
        )
        if command.lower() == 'u':
            undoLastTwoMoves(board)
            continue
        elif command.lower() == '?':
            printCommandOptions()
            continue
        elif command.lower() == 'l':
            printAllLegalMoves(board, parser)
            continue
        elif command.lower() == 'gm':
            printGameMoves(board.history)
        elif command.lower() == 'r':
            move = getRandomMove(board, parser)
        elif command.lower() == 'exit' or command.lower() == 'quit':
            return
        try:
            move = parser.parse(command)
        except ValueError as error:
            print('%s' % error)
            continue
        makeMove(move, board)


board = Board()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='chess',
        description='A python program to play chess '
        'against an AI in the terminal.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog='Enjoy the game!',
    )
    parser.add_argument(
        '-t',
        '--two',
        action='store_true',
        default=False,
        help='to play a 2-player game',
    )
    parser.add_argument(
        '-w',
        '--white',
        action='store',
        default='white',
        metavar='W',
        help='color for white player',
    )
    parser.add_argument(
        '-b',
        '--black',
        action='store',
        default='black',
        metavar='B',
        help='color for black player',
    )
    parser.add_argument(
        '-c',
        '--checkered',
        action='store_true',
        default=False,
        help='use checkered theme for the chess board',
    )

    args = parser.parse_args()
    board.whiteColor = args.white
    board.blackColor = args.black
    board.isCheckered = args.checkered
    try:
        if args.two:
            twoPlayerGame(board)
        else:
            playerSide = True
            board.currentSide = WHITE
            print()
            aiDepth = 2
            opponentAI = AI(board, not playerSide, aiDepth)
            printBoard(board)
            startGPT4Game(board, playerSide, opponentAI)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    main()

