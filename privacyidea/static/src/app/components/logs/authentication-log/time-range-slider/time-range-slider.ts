/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { Component, input, output } from "@angular/core";
import { MatSliderModule } from "@angular/material/slider";

/**
 * The authentication log's custom range slider over its activity histogram, with the exact range summarised below.
 *
 * A component of its own rather than markup in the log's template: Material's slider thumbs run change detection on
 * their view for every property they set while initialising, and in the log's template that view is the whole log,
 * table rows included. Here it is just this slider.
 */
@Component({
  selector: "app-time-range-slider",
  standalone: true,
  imports: [MatSliderModule],
  templateUrl: "./time-range-slider.html",
  styleUrl: "./time-range-slider.scss"
})
export class TimeRangeSlider {
  readonly histogram = input.required<number[]>();
  readonly steps = input.required<number>();
  readonly start = input.required<number>();
  readonly end = input.required<number>();
  readonly summaryFrom = input.required<string>();
  readonly summaryTo = input.required<string>();
  readonly displayWith = input.required<(pos: number) => string>();

  readonly startInput = output<number>();
  readonly endInput = output<number>();
  readonly commit = output<void>();
}
