# Falcos - art direction

Falcos is a lonely roadside gas station and convenience store at night. All art is new for this
game: nothing from the previous theme is used as a picture, reference or template. The HUD and the
black-and-white intro are kept from the base game unchanged.

## Look

High-end hand-inked cartoon illustration: bold, confident black outlines with varied line weight
(heavier on the outer edge and the shadow side), rich painterly form shading, fine material texture
(chipped paint, rust, worn chrome, cardboard fibre, foil crinkle, condensation on cold cans), and
small story details (price stickers, scuffs, a receipt corner). Symbols are cut-out objects with a
thin dark ink outline and a soft red neon kiss on the edge, not stickers.

## Lighting - the same for every image

- Key light: warm sodium-amber store light from the upper left, in front of the subject.
- Rim light: hot neon red (#FF2A3D) along the right and lower-right edges - the FALCOS sign.
- Fill: soft cool night blue from the front so the shadow side reads.
- Shadows: core shadows and occlusion lower right; any cast shadow falls down and to the right.

Prompt fragment:

> Lighting: warm amber key light from the upper left in front of the subject; a thin hot neon-red
> rim light along the right and lower-right edges; soft cool night-blue fill; core shadows and
> ambient occlusion lower right.

## Palette - neon diner at midnight

| role | colours |
|---|---|
| night | #070B18, #0E1630, #1B2547 |
| neon red (primary) | #FF2A3D glow, #E0102A tube, #FF9AA4 hot core, #6E0614 shade |
| sodium amber (secondary) | #FFB547, #E07A12, #FFE2A8 highlight |
| station paint | weathered cream #E9DFC9 and faded red #B7262E, rust #7A3B1C |
| wins and money | gold #F5C518, highlight #FFE58A, shade #8A5A00 |
| ink | #0A0A0F outlines |

## Symbol set

| id | tier | subject |
|---|---|---|
| H1 | top | a cash-register drawer stuffed with bills and coins |
| H2 | top | a gold winning lottery scratch ticket, half scratched, coins on it |
| H3 | top | a chrome classic-car key on a red FALCOS keychain tag |
| H4 | premium | a red gas-pump nozzle with its coiled hose |
| H5 | premium | a red metal jerry can |
| H6 | premium | a chrome flip-top lighter, lit |
| H7 | premium | a vintage motor-oil tin can |
| L1 | low | an ice-cold energy drink can with condensation |
| L2 | low | a giant blue-and-red slushie cup with straw |
| L3 | low | a roller-grill hot dog with mustard |
| L4 | low | a crinkly bag of chips |
| L5 | low | a candy bar half unwrapped |
| L6 | low | a paper cup of gas-station coffee, steaming |
| L7 | low | a pine-tree air freshener |
| L8 | low | a glazed donut with sprinkles |
| L9 | low | a pair of fuzzy dice |
| L10 | low | a stick of beef jerky in a wrapper |
| M | multiplier | a blank roadside gas-price sign panel (the game prints the value) |
| BS | scatter | the letters FS in red neon tube lettering on a small backing plate |
| ES | extreme scatter | the letters XFS in electric-blue neon tube lettering on a backing plate |

## Generation

- Model `openai/gpt-image-2.6-sunburst`, OpenRouter Images API, `quality: high`,
  `size: 3840x2160` for scenes, transparent background for cut-outs.
- `tools/falcos/orgen.py` reads `~/.falcos/openrouter-key.txt` (never printed, never committed)
  and logs every image's cost to `art/falcos/cost_log.jsonl`.
- Animated layers (neon flicker, smoke, character idle) are composited and rendered in Blender
  from the generated plates at 3840x2160 masters, then downsized for the game.
