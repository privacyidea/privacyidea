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
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  linkedSignal,
  OnInit,
  output,
  Signal
} from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormRecord,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn
} from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { Observable, of, Subscription } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { QuestionApiPayloadMapper } from "../../../../mappers/token-api-payload/question-token-api-payload.mapper";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

export interface QuestionEnrollmentOptions extends TokenEnrollmentData {
  type: "question";
  answers: Record<string, string>;
}

@Component({
  selector: "app-enroll-question",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: "./enroll-question.component.html",
  styleUrl: "./enroll-question.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EnrollQuestionComponent implements OnInit {
  protected readonly enrollmentMapper: QuestionApiPayloadMapper = inject(QuestionApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  readonly configMinNumberOfAnswers: Signal<number> = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return cfg && cfg["question.num_answers"] ? parseInt(cfg["question.num_answers"], 10) : 0;
  });
  private readonly guardControl = new FormControl<boolean>(false, { nonNullable: true });
  private valueSubscription?: Subscription;
  additionalFormFieldsChange = output<{ [key: string]: FormControl<unknown> }>();
  clickEnrollChange = output<(basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>>();
  configQuestions = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith("question.question."))
      .map(([, v]) => ({ question: String(v) }));
  });

  questionControlNames = computed(() => this.configQuestions().map((q) => `answer_${q.question.replace(/\s+/g, "_")}`));

  questionForm = linkedSignal({
    source: () => this.questionControlNames(),
    computation: (names) => {
      if (this.valueSubscription) {
        this.valueSubscription.unsubscribe();
        this.valueSubscription = undefined;
      }
      const form = new FormRecord<FormControl<string>>({});
      names.forEach((n) => form.addControl(n, new FormControl<string>("", { nonNullable: true })));
      const validator = this.minAnswersValidatorFor(form);
      form.setValidators(validator);
      this.guardControl.setValidators(validator);
      form.updateValueAndValidity({ emitEvent: false });
      this.guardControl.updateValueAndValidity({ emitEvent: false });
      this.valueSubscription = form.valueChanges.subscribe(() => {
        this.guardControl.updateValueAndValidity({ emitEvent: false });
      });
      this.additionalFormFieldsChange.emit({ __questionsGuard: this.guardControl });
      return form;
    }
  });

  ngOnInit(): void {
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    const form = this.questionForm();
    if (form.invalid) {
      form.markAllAsTouched();
      return of(null);
    }

    const answers: Record<string, string> = {};
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, "_")}`;
      if (this.questionForm().get(controlName)?.value !== "") {
        answers[q.question] = this.questionForm().get(controlName)?.value;
      }
    });
    const enrollmentData: QuestionEnrollmentOptions = { ...basicOptions, type: "question", answers };
    return this.tokenService.enrollToken({ data: enrollmentData, mapper: this.enrollmentMapper });
  };

  private answeredCount(form: FormRecord<FormControl<string>>): number {
    return Object.values(form.controls).filter((c) => (c.value ?? "").toString().trim() !== "").length;
  }

  private minAnswersValidatorFor(form: FormRecord<FormControl<string>>): ValidatorFn {
    return (_: AbstractControl): ValidationErrors | null => {
      const required = this.configMinNumberOfAnswers();
      const actual = this.answeredCount(form);
      return actual >= required ? null : { minAnswers: { required, actual } };
    };
  }
}
