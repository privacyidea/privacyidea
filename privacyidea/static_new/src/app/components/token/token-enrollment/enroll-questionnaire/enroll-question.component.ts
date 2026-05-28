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
import { ChangeDetectionStrategy, Component, computed, inject, input, linkedSignal, OnInit, signal, Signal, output } from '@angular/core';
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  QuestionApiPayloadMapper,
  QuestionEnrollmentData
} from "@app/mappers/token-api-payload/question-token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { QUESTION_CONFIG_PREFIX, QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface QuestionEnrollmentOptions extends TokenEnrollmentData {
  type: "question";
  answers: Record<string, string>;
}

@Component({
  selector: "app-enroll-question",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, MatError],
  templateUrl: "./enroll-question.component.html",
  styleUrl: "./enroll-question.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EnrollQuestionComponent implements OnInit {
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

  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: QuestionEnrollmentData;
      mapper: TokenApiPayloadMapper<QuestionEnrollmentData>;
    } | null>();
  disabled = input<boolean>(false);

  configQuestions = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return [];
    const cfg = this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith(QUESTION_CONFIG_PREFIX))
      .map(([, v]) => ({ question: String(v) }));
  });

  answers = linkedSignal<{ question: string }[], Record<string, string>>({
    source: this.configQuestions,
    computation: (questions, prev) => {
      const prevAnswers: Record<string, string> = prev?.value ?? {};
      const next: Record<string, string> = {};
      questions.forEach((q) => {
        next[q.question] = prevAnswers[q.question] ?? "";
      });
      return next;
    }
  });

  formTouched = signal<boolean>(false);

  answeredCount = computed(() => Object.values(this.answers()).filter((v) => v.trim() !== "").length);

  setAnswer(question: string, value: string): void {
    this.answers.update((prev) => ({ ...prev, [question]: value }));
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: QuestionEnrollmentData;
    mapper: TokenApiPayloadMapper<QuestionEnrollmentData>;
  } | null => {
    if (this.answeredCount() < this.configMinNumberOfAnswers()) {
      this.formTouched.set(true);
      return null;
    }

    const answers: Record<string, string> = {};
    this.configQuestions().forEach((q) => {
      const answer = this.answers()[q.question];
      if (answer && answer.trim() !== "") {
        answers[q.question] = answer;
      }
    });

    const enrollmentData: QuestionEnrollmentOptions = { ...basicOptions, type: "question", answers };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  goToQuestionConfig() {
    this.contentService.router.navigate([ROUTE_PATHS.CONFIGURATION_TOKENTYPES], { fragment: "questionnaire" });
  }

  onQuestionConfigKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      this.goToQuestionConfig();
    }
  }
}
