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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { HttpResourceRef, provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { SystemConfigResponse, SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { flushFixture, typeInto } from "@testing/enroll-form-dom";
import { MockContentService, MockSystemService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { EnrollQuestionComponent } from "./enroll-question.component";

describe("EnrollQuestionnaireComponent", () => {
  let component: EnrollQuestionComponent;
  let fixture: ComponentFixture<EnrollQuestionComponent>;
  let systemService: MockSystemService;

  const basicOptions: TokenEnrollmentData = { type: "question" } as TokenEnrollmentData;

  const configure = (questions: string[], numAnswers?: number) => {
    const config: Record<string, string> = {};
    questions.forEach((question, index) => (config[`question.question.Q${index}`] = question));
    if (numAnswers !== undefined) config["question.num_answers"] = String(numAnswers);
    (systemService.systemConfigResource as HttpResourceRef<SystemConfigResponse | undefined>).value.set(
      MockPiResponse.fromValue(config)
    );
  };
  const inputs = (): HTMLInputElement[] => Array.from(fixture.nativeElement.querySelectorAll("input"));

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollQuestionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    fixture = TestBed.createComponent(EnrollQuestionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("answers form", () => {
    beforeEach(async () => {
      configure(["Pet?", "Street?", "School?"], 2);
      await flushFixture(fixture);
    });

    it("renders one input per configured question", () => {
      expect(inputs()).toHaveLength(3);
      expect(fixture.nativeElement.textContent).toContain("Street?");
    });

    it("is invalid until the minimum number of answers is filled in", async () => {
      expect(component.answersForm().valid()).toBe(false);

      await typeInto(fixture, inputs()[0], "Rex");
      expect(component.answersForm().valid()).toBe(false);

      await typeInto(fixture, inputs()[2], "Hill");
      expect(component.answersForm().valid()).toBe(true);
    });

    it("does not count a whitespace-only answer", async () => {
      await typeInto(fixture, inputs()[0], "Rex");
      await typeInto(fixture, inputs()[1], "   ");

      expect(component.answeredCount()).toBe(1);
      expect(component.answersForm().valid()).toBe(false);
    });

    it("writes typed text to the row and marks it dirty", async () => {
      await typeInto(fixture, inputs()[1], "Main");

      expect(component.answers()[1]).toMatchObject({ question: "Street?", answer: "Main" });
      expect(component.answersForm[1].answer().dirty()).toBe(true);
    });

    it("refuses the build, touches the form and renders the error", async () => {
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

      expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
      await flushFixture(fixture);

      expect(component.answersForm().touched()).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("At least 2 answers");
    });

    it("builds the answers of the filled rows only", async () => {
      await typeInto(fixture, inputs()[0], "Rex");
      await typeInto(fixture, inputs()[2], "Hill");

      const args = component.buildEnrollmentArgs(basicOptions);

      expect(args?.data).toEqual(
        expect.objectContaining({ type: "question", answers: { "Pet?": "Rex", "School?": "Hill" } })
      );
    });

    it("keeps typed answers when the configured questions change", async () => {
      await typeInto(fixture, inputs()[0], "Rex");

      configure(["Pet?", "Car?"], 2);
      await flushFixture(fixture);

      expect(component.answers()).toMatchObject([
        { question: "Pet?", answer: "Rex" },
        { question: "Car?", answer: "" }
      ]);
    });
  });

  it("keeps two questions with the same text as two rows", async () => {
    configure(["Pet?", "Pet?"], 1);
    await flushFixture(fixture);

    expect(inputs()).toHaveLength(2);
    await typeInto(fixture, inputs()[1], "Rex");
    expect(component.answers().map((row) => row.answer)).toEqual(["", "Rex"]);
  });

  it("defaults to five required answers without a configured number", () => {
    expect(component.configMinNumberOfAnswers()).toBe(5);
  });
});
