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
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  forwardRef,
  inject,
  linkedSignal,
  Signal
} from "@angular/core";
import { form, FormField, validate } from "@angular/forms/signals";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  QuestionApiPayloadMapper,
  QuestionEnrollmentData
} from "@app/mappers/token-api-payload/question-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { QUESTION_CONFIG_PREFIX, QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";

export interface QuestionAnswer {
  question: string;
  answer: string;
}

export interface QuestionEnrollmentOptions extends TokenEnrollmentData {
  type: "question";
  answers: Record<string, string>;
}

@Component({
  selector: "app-enroll-question",
  standalone: true,
  imports: [FormField, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: "./enroll-question.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollQuestionComponent) }
  ]
})
export class EnrollQuestionComponent extends EnrollTokenBase<QuestionEnrollmentData> {
  protected readonly enrollmentMapper: QuestionApiPayloadMapper = inject(QuestionApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly configMinNumberOfAnswers: Signal<number> = computed(() => {
    const defaultQuestions = 5;
    if (!this.systemService.systemConfigResource.hasValue()) return defaultQuestions;
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return cfg && cfg[QUESTION_NUMBER_OF_ANSWERS] ? parseInt(cfg[QUESTION_NUMBER_OF_ANSWERS], 10) : defaultQuestions;
  });

  configQuestions = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return [];
    const cfg = this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith(QUESTION_CONFIG_PREFIX))
      .map(([, v]) => ({ question: String(v) }));
  });

  // A list keeps two configured questions with the same text as two separate rows.
  answers = linkedSignal<{ question: string }[], QuestionAnswer[]>({
    source: this.configQuestions,
    computation: (questions, prev) => {
      const prevAnswers = new Map((prev?.value ?? []).map((row): [string, string] => [row.question, row.answer]));
      return questions.map((q) => ({ question: q.question, answer: prevAnswers.get(q.question) ?? "" }));
    }
  });

  answeredCount = computed(() => this.answers().filter((row) => row.answer.trim() !== "").length);

  answersForm = form(this.answers, (f) => {
    validate(f, () => (this.answeredCount() < this.configMinNumberOfAnswers() ? [{ kind: ERR.required }] : []));
  });

  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<QuestionEnrollmentData> | null {
    if (!this.answersForm().valid()) {
      void touchAll(this.answersForm);
      return null;
    }

    const answers: Record<string, string> = {};
    for (const row of this.answers()) {
      if (row.answer.trim() !== "") {
        answers[row.question] = row.answer;
      }
    }

    const enrollmentData: QuestionEnrollmentOptions = { ...basicOptions, type: "question", answers };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  goToQuestionConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: "questionnaire" });
  }

  onQuestionConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToQuestionConfig();
    }
  }
}
