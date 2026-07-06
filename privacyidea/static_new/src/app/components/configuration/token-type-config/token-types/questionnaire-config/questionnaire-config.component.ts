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

import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";

@Component({
  selector: "app-questionnaire-config",
  standalone: true,
  imports: [MatExpansionModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule],
  templateUrl: "./questionnaire-config.component.html",
  styleUrl: "./questionnaire-config.component.scss"
})
export class QuestionnaireConfigComponent {
  protected readonly QUESTION_NUMBER_OF_ANSWERS = QUESTION_NUMBER_OF_ANSWERS;

  formData = input.required<Record<string, string>>();
  questionKeys = input.required<string[]>();
  expanded = input<boolean>(false);

  formDataChange = output<Record<string, string>>();
  addQuestionRequest = output<void>();
  deleteRequest = output<string>();

  blockNonNumeric(event: KeyboardEvent): void {
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && (event.key < "0" || event.key > "9")) {
      event.preventDefault();
    }
  }

  updateFormData(fieldName: string, value: string): void {
    const newValue = { ...this.formData(), [fieldName]: value };
    this.formDataChange.emit(newValue);
  }

  addQuestion() {
    this.addQuestionRequest.emit();
  }

  deleteEntry(key: string) {
    this.deleteRequest.emit(key);
  }
}
