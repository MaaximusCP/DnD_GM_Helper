import re
import secrets

from app.domain.models import DiceRollRequest


class DiceService:
    """Motor local de daus amb límits segurs i regles d'avantatge de l'SRD 5.1."""

    NOTATION = re.compile(r"(\d{1,2})d(\d{1,3})([+-]\d{1,4})?")

    @classmethod
    def roll(cls, payload: DiceRollRequest) -> dict:
        notation = payload.notation.replace(" ", "").lower()
        match = cls.NOTATION.fullmatch(notation)
        if not match:
            raise ValueError("Notació no vàlida; utilitza per exemple 1d20+5")
        count, sides, modifier = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
        if count > 20 or sides > 100 or sides < 2:
            raise ValueError("La tirada supera els límits permesos")
        if payload.mode != "normal" and (count != 1 or sides != 20):
            raise ValueError("L'avantatge i el desavantatge només s'apliquen a una tirada d'1d20")

        rolled_count = 2 if payload.mode != "normal" else count
        dice = [secrets.randbelow(sides) + 1 for _ in range(rolled_count)]
        if payload.mode == "advantage":
            kept = [max(dice)]
        elif payload.mode == "disadvantage":
            kept = [min(dice)]
        else:
            kept = dice.copy()
        total = sum(kept) + modifier
        natural = kept[0] if count == 1 and sides == 20 else None
        return {
            "notation": notation, "dice": dice, "kept": kept, "modifier": modifier, "total": total,
            "success": total >= payload.dc if payload.dc is not None else None,
            "critical": "success" if natural == 20 else "failure" if natural == 1 else None,
        }
