import {
  animate,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';

export const tabToggleState = trigger('toggleState', [
  state(
    '*',
    style({
      transform: 'translateY(0)',
    }),
  ),
  transition('false => true', [
    style({
      transform: 'translateY(60%)',
    }),
    animate(
      '400ms ease-in',
      style({
        transform: 'translateY(0)',
      }),
    ),
  ]),
  transition('true => false', [
    style({
      transform: 'translateY(60%)',
    }),
    animate(
      '400ms ease-out',
      style({
        transform: 'translateY(0)',
      }),
    ),
  ]),
]);
