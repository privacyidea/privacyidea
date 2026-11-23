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
import { FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import {
  panelCompleteness,
  TokenTypeConfigForm
} from "@components/configuration/token-type-config/token-type-config.form";
import { PanelIncompleteComponent } from "@components/configuration/token-type-config/token-types/panel-incomplete/panel-incomplete.component";
import { QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

@Component({
  selector: "app-questionnaire-config",
  standalone: true,
  imports: [
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    FormField,
    PanelIncompleteComponent
  ],
  templateUrl: "./questionnaire-config.component.html",
  styleUrl: "./questionnaire-config.component.scss"
})
export class QuestionnaireConfigComponent {
  protected readonly QUESTION_NUMBER_OF_ANSWERS = QUESTION_NUMBER_OF_ANSWERS;
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  config = input.required<TokenTypeConfigForm>();
  questionKeys = input.required<string[]>();
  expanded = input<boolean>(false);
  protected readonly panel = panelCompleteness(this.config, () => [QUESTION_NUMBER_OF_ANSWERS, ...this.questionKeys()]);

  addQuestionRequest = output<void>();
  deleteRequest = output<string>();

  addQuestion() {
    this.addQuestionRequest.emit();
  }

  deleteEntry(key: string) {
    this.deleteRequest.emit(key);
  }
}
