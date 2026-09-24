// The three values `recommendation` can take (backend enum: egg_coffee /
// iced_milk_coffee / other, plus null when a guardrail blocked the prompt and
// no model ran).
//
// Nothing secret lives here: these are values the API returns on every turn,
// and both drink names are already public in `instructions_vi`. The forbidden
// list and the solution paths stay on the backend.

export interface Drink {
  label: string;
  image: string;
  /** describes the picture, not the game state */
  alt: string;
  width: number;
  height: number;
}

export const DRINKS: Record<string, Drink> = {
  egg_coffee: {
    label: "Cà phê trứng",
    image: "/image/egg-coffee.png",
    alt: "Ly cà phê trứng trên bàn gỗ, phố cà phê Hà Nội phía sau",
    width: 1408,
    height: 768,
  },
  iced_milk_coffee: {
    label: "Cà phê sữa đá",
    image: "/image/iced-coffee.png",
    alt: "Ly cà phê sữa đá với phin nhôm đặt trên miệng ly",
    width: 1408,
    height: 768,
  },
  other: {
    label: "Món khác",
    image: "",
    alt: "",
    width: 0,
    height: 0,
  },
};

export function drinkFor(
  recommendation: string | null | undefined,
): Drink | null {
  if (!recommendation) return null;
  return DRINKS[recommendation] ?? null;
}
