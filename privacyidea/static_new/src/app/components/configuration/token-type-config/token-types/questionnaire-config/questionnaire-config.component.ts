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
import { Component, input, output, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatDivider } from "@angular/material/list";

@Component({
  selector: "app-questionnaire-config",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatDivider
  ],
  templateUrl: "./questionnaire-config.component.html",
  styleUrl: "./questionnaire-config.component.scss"
})
export class QuestionnaireConfigComponent {
  formData = input.required<Record<string, any>>();
  questionKeys = input.required<string[]>();

  onAddQuestion = output<string>();
  onDeleteEntry = output<string>();

  newQuestionText = signal("");

  addQuestion() {
    if (this.newQuestionText()) {
      this.onAddQuestion.emit(this.newQuestionText());
      this.newQuestionText.set("");
    }
  }

  deleteEntry(key: string) {
    this.onDeleteEntry.emit(key);
  }
}
