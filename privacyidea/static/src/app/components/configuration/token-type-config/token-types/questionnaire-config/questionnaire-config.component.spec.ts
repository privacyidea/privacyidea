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
import { provideRouter } from "@angular/router";
import { QuestionnaireConfigComponent } from "@components/configuration/token-type-config/token-types/questionnaire-config/questionnaire-config.component";
import { QUESTION_NUMBER_OF_ANSWERS } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import { touchAll } from "@utils/form-state.utils";

const mockQuestionKeys = ["question.question.1", "question.question.2", "question.question.3"];
const filledConfig = () => ({
  [QUESTION_NUMBER_OF_ANSWERS]: "2",
  "question.question.1": "Q1",
  "question.question.2": "Q2",
  "question.question.3": "Q3"
});

describe("QuestionnaireConfigComponent", () => {
  let fixture: ComponentFixture<QuestionnaireConfigComponent>;
  let component: QuestionnaireConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const answersInput = () => fixture.nativeElement.querySelector("input[type=number]") as HTMLInputElement;
  const questionInputs = () =>
    Array.from(fixture.nativeElement.querySelectorAll(".questionnaire-grid input") as NodeListOf<HTMLInputElement>);
  const type = async (element: HTMLInputElement, value: string) => {
    element.value = value;
    element.dispatchEvent(new Event("input"));
    await flush();
  };
  const errors = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map((error) =>
      error.textContent?.trim()
    );

  const create = async (config: Record<string, string> = filledConfig(), questionKeys: string[] = mockQuestionKeys) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(QuestionnaireConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("questionKeys", questionKeys);
    component = fixture.componentInstance;
    await flush();
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QuestionnaireConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("shows the number of answers and the questions of the form", async () => {
    await create(filledConfig());

    expect(answersInput().value).toBe("2");
    expect(questionInputs().map((element) => element.value)).toEqual(["Q1", "Q2", "Q3"]);
  });

  it("writes the typed number of answers and question to the form", async () => {
    await create(filledConfig());

    await type(answersInput(), "10");
    await type(questionInputs()[1], "Changed");

    expect(configForm.model().values[QUESTION_NUMBER_OF_ANSWERS]).toBe("10");
    expect(configForm.model().values["question.question.2"]).toBe("Changed");
    expect(configForm.form.values["question.question.2"]().dirty()).toBe(true);
  });

  it("should emit addQuestionRequest when addQuestion is called", async () => {
    await create();
    jest.spyOn(component.addQuestionRequest, "emit");
    component.addQuestion();
    expect(component.addQuestionRequest.emit).toHaveBeenCalled();
  });

  it("should emit deleteRequest when deleteEntry is called", async () => {
    await create();
    jest.spyOn(component.deleteRequest, "emit");
    const keyToDelete = "question.question.1";
    component.deleteEntry(keyToDelete);
    expect(component.deleteRequest.emit).toHaveBeenCalledWith(keyToDelete);
  });

  it("should emit deleteRequest when a delete button is clicked", async () => {
    await create(filledConfig());
    jest.spyOn(component.deleteRequest, "emit");

    (fixture.nativeElement.querySelectorAll(".questionnaire-grid button")[2] as HTMLButtonElement).click();

    expect(component.deleteRequest.emit).toHaveBeenCalledWith("question.question.3");
  });

  it("should handle multiple question keys", async () => {
    await create(filledConfig());
    const multipleKeys = [...mockQuestionKeys, "question.question.4"];
    configForm.model.update((model) => ({ ...model, values: { ...model.values, "question.question.4": "Q4" } }));
    fixture.componentRef.setInput("questionKeys", multipleKeys);
    await flush();

    expect(component.questionKeys().length).toBe(4);
    expect(questionInputs().map((element) => element.value)).toEqual(["Q1", "Q2", "Q3", "Q4"]);
  });

  it("should handle empty question keys array", async () => {
    await create({}, []);
    expect(component.questionKeys().length).toBe(0);
    expect(questionInputs().length).toBe(0);
  });

  describe("number of answers input", () => {
    it("writes an empty string when the input is cleared", async () => {
      await create({ [QUESTION_NUMBER_OF_ANSWERS]: "2" }, []);

      await type(answersInput(), "");

      expect(configForm.model().values[QUESTION_NUMBER_OF_ANSWERS]).toBe("");
    });

    it("does not require the number of answers once a question exists, the backend defaults it", async () => {
      await create({ "question.question.1": "Q1" }, ["question.question.1"]);

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("shows a message for text the number input cannot parse", async () => {
      await create({ [QUESTION_NUMBER_OF_ANSWERS]: "2" }, []);
      Object.defineProperty(answersInput(), "validity", { value: { badInput: true } });

      await type(answersInput(), "");
      configForm.form.values[QUESTION_NUMBER_OF_ANSWERS]().markAsTouched();
      await flush();

      expect(errors()).toEqual(["Enter a valid number."]);
      expect(configForm.form().valid()).toBe(false);
      expect(fixture.nativeElement.querySelector(".panel-incomplete")?.textContent).toContain("Incomplete");
    });

    it("shows a message for a number that is not a whole number", async () => {
      await create({ [QUESTION_NUMBER_OF_ANSWERS]: "2" }, []);

      await type(answersInput(), "-1");
      configForm.form.values[QUESTION_NUMBER_OF_ANSWERS]().markAsTouched();
      await flush();

      expect(errors()).toEqual(["Number of Answers must be a whole number."]);
      expect(configForm.form().valid()).toBe(false);
    });
  });

  describe("question inputs", () => {
    it("shows the error of an empty question once the form is touched", async () => {
      await create({ ...filledConfig(), "question.question.2": "" });
      expect(errors()).toEqual([]);

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual(["Question must not be empty."]);
    });

    it("removes the error once the question is filled", async () => {
      await create({ ...filledConfig(), "question.question.2": "" });
      await touchAll(configForm.form);
      await flush();

      await type(questionInputs()[1], "Filled");

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });
  });
});
