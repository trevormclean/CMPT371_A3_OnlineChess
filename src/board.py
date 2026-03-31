""" board.py defines the chess board and game logic """

from copy import deepcopy
from dataclasses import dataclass

WHITE = "white"
BLACK = "black"

# interface for pieces
class Piece:
  symbol = ""

  # directions is a list of places the piece can move
  # the tuple is [slidable, row, column]
  directions: list[tuple[bool, int, int]] = []

  def __init__(self, color):
    self.color = color

class Pawn(Piece):
  symbol = "P"
  def __init__(self, color):
    self.color = color
    self.directions = [(False, 1 if color == WHITE else -1, 0)]

class Rook(Piece):
  symbol = "R"
  directions = [(True, 0, 1), (True, 0, -1), (True, 1, 0), (True, -1, 0)]

class Bishop(Piece):
  symbol = "B"
  directions = [(True, 1, 1), (True, 1, -1), (True, -1, 1), (True, -1, -1)]

class Knight(Piece):
  symbol = "N"
  directions = [(False, 1, 2), (False, 2, 1), (False, -1, 2), (False, 2, -1), (False, 1, -2), (False, -2, 1), (False, -1, -2), (False, -2, -1)]

class Queen(Piece):
  symbol = "Q"
  directions = [(True, 0, 1), (True, 0, -1), (True, 1, 0), (True, -1, 0), (True, 1, 1), (True, 1, -1), (True, -1, 1), (True, -1, -1)]

class King(Piece):
  symbol = "K"
  directions = [(False, 0, 1), (False, 0, -1), (False, 1, 0), (False, -1, 0), (False, 1, 1), (False, 1, -1), (False, -1, 1), (False, -1, -1)]


@dataclass
class Move:
  start: tuple[int, int]
  end: tuple[int, int]
  promotion: type[Piece] | None = None
  en_passant: bool = False
  kside_castle: bool = False
  qside_castle: bool = False

class Board:
  grid: list[list[Piece | None]]
  turn: str # WHITE or BLACK
  en_passant_square: tuple[int, int] | None # the square where en passant is possible
  castling_rights: dict[str, dict[str, bool]] 

  def __init__(self):
      self.grid = [[None for _ in range(8)] for _ in range(8)]
      self.turn = WHITE
      self.en_passant_square = None
      self.castling_rights = {
        WHITE: {"K": True, "Q": True},
        BLACK: {"K": True, "Q": True},
      }

      self._setup()
  
  # Helpers _________________________________________________________________
  def _setup(self):
    back = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
    for col, piece in enumerate(back):
      self.grid[0][col] = piece(WHITE)
      self.grid[1][col] = Pawn(WHITE)

      self.grid[7][col] = piece(BLACK)
      self.grid[6][col] = Pawn(BLACK)

  def _opponent(self, color: str) -> str:
    return BLACK if color == WHITE else WHITE
  
  def _in_bounds(self, row: int, col: int) -> bool:
    return 0 <= row < 8 and 0 <= col < 8

  # Attack detection _________________________________________________________________
  def _get_attacks(self, row: int, col: int) -> list[tuple[int, int]]:
    """Returns every square attacked by the piece at (row, col)"""
    piece = self.grid[row][col]
    if piece is None:
        return []
    
    attacked: list[tuple[int, int]] = []

    if isinstance(piece, Pawn):
      dr = piece.directions[0][1]
      for dc in (-1, 1):
        if self._in_bounds(row + dr, col + dc):
          attacked.append((row + dr, col + dc))
      return attacked
    
    for slidable, dr, dc in piece.directions:
      if slidable:
        r, c = row + dr, col + dc
        while self._in_bounds(r, c):
          attacked.append((r, c))
          if self.grid[r][c] is not None:  # can't slide past a piece
            break
          r += dr
          c += dc
      else:
        r, c = row + dr, col + dc
        if self._in_bounds(r, c):
          attacked.append((r, c))

    return attacked

  def _square_attacked_by(self, row: int, col: int, attacker_color: str) -> bool:
    """Returns True if (row, col) is attacked by any piece of attacker_color"""
    for r in range(8):
      for c in range(8):
        p = self.grid[r][c]
        if p is not None and p.color == attacker_color:
          if (row, col) in self._get_attacks(r, c):
            return True
    return False

  def in_check(self, color: str) -> bool:
    """Returns True if color is in check"""
    for r in range(8):
      for c in range(8):
        p = self.grid[r][c]
        if isinstance(p, King) and p.color == color:
          return self._square_attacked_by(r, c, self._opponent(color))
    
  # Move generation ____________________________________________________________
  def _candidate_legal_moves(self, row: int, col: int) -> list[Move]:
    """
    Generates candidate moves for the piece at (row, col) without checking
    whether the resulting position leaves the mover's king in check.
    """
    piece = self.grid[row][col]
    if piece is None:
      return []

    # pawns have unusual moves
    if isinstance(piece, Pawn):
      return self._pawn_moves(row, col, piece)

    # have to consider castling separately
    if isinstance(piece, King):
      return self._king_moves(row, col, piece)

    moves: list[Move] = []
    for slidable, dr, dc in piece.directions:
      if slidable:
        r, c = row + dr, col + dc
        while self._in_bounds(r, c):
          target = self.grid[r][c]
          if target is None:
            moves.append(Move((row, col), (r, c)))
          elif target.color != piece.color:
            moves.append(Move((row, col), (r, c)))
            break  # capture then stop sliding
          else:
            break  # own piece blocks
          r += dr
          c += dc
      else:
        r, c = row + dr, col + dc
        if self._in_bounds(r, c):
          target = self.grid[r][c]
          if target is None or target.color != piece.color:
            moves.append(Move((row, col), (r, c)))

    return moves

  def _pawn_moves(self, row: int, col: int, piece: Pawn) -> list[Move]:
    """Helper for _candidate_legal_moves(), returning all moves for a pawn."""
    moves = []
    dr = piece.directions[0][1]
    r = row + dr
    promo_row = 7 if piece.color == WHITE else 0

    if not self._in_bounds(r, col):
      return []

    # forward moves
    if self.grid[r][col] is None:
      if r == promo_row:
        for p in (Queen, Rook, Bishop, Knight):
          moves.append(Move((row, col), (r, col), promotion=p))
      else:
        moves.append(Move((row, col), (r, col)))
        r2 = row + 2 * dr # double push available from starting row
        if ((piece.color == WHITE and row == 1) or (piece.color == BLACK and row == 6)) and self.grid[r2][col] is None:
          moves.append(Move((row, col), (r2, col)))

    # diagonal captures
    for dc in (-1, 1):
      c = col + dc
      if not self._in_bounds(r, c):
        continue
      target = self.grid[r][c]
      if target is not None and target.color != piece.color:
        if r == promo_row:
          for p in (Queen, Rook, Bishop, Knight):
            moves.append(Move((row, col), (r, c), promotion=p))
        else:
          moves.append(Move((row, col), (r, c)))
      elif (r, c) == self.en_passant_square:
        moves.append(Move((row, col), (r, c), en_passant=True))

    return moves

  def _king_moves(self, row: int, col: int, king: King) -> list[Move]:
    """Helper for _candidate_legal_moves(), returning all moves for a king."""
    opponent = self._opponent(king.color)
    moves = []

    for _, dr, dc in king.directions:
      r, c = row + dr, col + dc
      if self._in_bounds(r, c):
        target = self.grid[r][c]
        if target is None or target.color != king.color:
          moves.append(Move((row, col), (r, c)))

    # === castling ===

    # king can't be in check
    if self.in_check(king.color):
      return moves

    rights = self.castling_rights[king.color]

    # for kingside castle, f/g must be empty and unthreatened
    if rights["K"]:
      if self.grid[row][5] is None and self.grid[row][6] is None:
        if not self._square_attacked_by(row, 5, opponent) and not self._square_attacked_by(row, 6, opponent):
          moves.append(Move((row, col), (row, 6), kside_castle=True))

    # for queenside castle, b/c/d must be empty; c and d must be unthreatened
    if rights["Q"]:
      if self.grid[row][1] is None and self.grid[row][2] is None and self.grid[row][3] is None:
        if not self._square_attacked_by(row, 2, opponent) and not self._square_attacked_by(row, 3, opponent):
          moves.append(Move((row, col), (row, 2), qside_castle=True))

    return moves

  # Legal move filtering ____________________________________________________
  def _leaves_in_check(self, move: Move) -> bool:
    """Returns True if making the move leaves the mover's king in check."""
    board_copy = deepcopy(self)
    board_copy.apply_move(move)
    return board_copy.in_check(self.turn)  # self.turn = the color that just moved

  def get_legal_moves(self, row: int, col: int) -> list[Move]:
    """All legal moves for the piece at (row, col)."""
    piece = self.grid[row][col]
    if piece is None:
      return []
    return [m for m in self._candidate_legal_moves(row, col) if not self._leaves_in_check(m)]

  def get_all_legal_moves(self) -> list[Move]:
    """All legal moves available to the current player."""
    moves: list[Move] = []
    for r in range(8):
      for c in range(8):
        p = self.grid[r][c]
        if p is not None and p.color == self.turn:
          moves.extend(self.get_legal_moves(r, c))
    return moves

  # Move execution ______________________________________________________
  def apply_move(self, move: Move) -> None:
    """Unconditionally applies the move and updates the board state."""
    sr, sc = move.start
    er, ec = move.end
    piece = self.grid[sr][sc]

    # update castling rights
    if isinstance(piece, King):
      self.castling_rights[piece.color]["K"] = False
      self.castling_rights[piece.color]["Q"] = False
    elif isinstance(piece, Rook):
      if sc == 0:
        self.castling_rights[piece.color]["Q"] = False
      elif sc == 7:
        self.castling_rights[piece.color]["K"] = False

    # rook captured on its starting square also loses castling rights
    captured = self.grid[er][ec]
    if isinstance(captured, Rook):
      if ec == 0:
        self.castling_rights[captured.color]["Q"] = False
      elif ec == 7:
        self.castling_rights[captured.color]["K"] = False

    # update en passant
    self.en_passant_square = None
    if isinstance(piece, Pawn) and abs(er - sr) == 2:
      self.en_passant_square = ((sr + er) // 2, sc)

    if move.en_passant:
        self.grid[sr][ec] = None # remove captured pawn

    # move rook if castling
    if move.kside_castle:
        self.grid[sr][5] = self.grid[sr][7]
        self.grid[sr][7] = None 
    elif move.qside_castle:
        self.grid[sr][3] = self.grid[sr][0]
        self.grid[sr][0] = None

    # move piece
    self.grid[er][ec] = piece
    self.grid[sr][sc] = None

    if move.promotion is not None:
        self.grid[er][ec] = move.promotion(piece.color)

    # alternate turn 
    self.turn = self._opponent(self.turn)

  #  Game state checks ________________________________________________
  def is_checkmate(self) -> bool:
    return self.in_check(self.turn) and not self.get_all_legal_moves()

  def is_stalemate(self) -> bool:
    return not self.in_check(self.turn) and not self.get_all_legal_moves()

  def is_game_over(self) -> bool:
    return self.is_checkmate() or self.is_stalemate()
