import { animate, state, style, transition, trigger } from "@angular/animations";

export const tabToggleState = trigger("toggleState", [
  state(
    "*",
    style({
      transform: "translateY(0)"
    })
  ),
  transition("* => *", [
    style({
      transform: "translateY(60%)"
    }),
    animate(
      "400ms ease-in",
      style({
        transform: "translateY(0)"
      })
    )
  ]),
  transition("* => *", [
    style({
      transform: "translateY(60%)"
    }),
    animate(
      "400ms ease-out",
      style({
        transform: "translateY(0)"
      })
    )
  ])
]);

export const componentFadeAnimation = trigger("componentFade", [
  transition(":enter", [style({ opacity: 0 }), animate("150ms ease-out", style({ opacity: 1 }))])
]);
