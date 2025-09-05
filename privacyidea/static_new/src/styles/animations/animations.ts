/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
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
