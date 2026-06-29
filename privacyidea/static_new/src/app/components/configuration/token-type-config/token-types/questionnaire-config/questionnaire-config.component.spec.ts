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

const mockQuestionKeys = ["question.question.1", "question.question.2", "question.question.3"];

describe("QuestionnaireConfigComponent", () => {
  let fixture: ComponentFixture<QuestionnaireConfigComponent>;
  let component: QuestionnaireConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QuestionnaireConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(QuestionnaireConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("questionKeys", mockQuestionKeys);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "10";
    component.updateFormData(QUESTION_NUMBER_OF_ANSWERS, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [QUESTION_NUMBER_OF_ANSWERS]: newValue });
  });

  it("should display current formData value for num_answers", () => {
    const testData = {
      [QUESTION_NUMBER_OF_ANSWERS]: 7
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[QUESTION_NUMBER_OF_ANSWERS]).toEqual(7);
  });

  it("should emit addQuestionRequest when addQuestion is called", () => {
    jest.spyOn(component.addQuestionRequest, "emit");
    component.addQuestion();
    expect(component.addQuestionRequest.emit).toHaveBeenCalled();
  });

  it("should emit deleteRequest when deleteEntry is called", () => {
    jest.spyOn(component.deleteRequest, "emit");
    const keyToDelete = "question.question.1";
    component.deleteEntry(keyToDelete);
    expect(component.deleteRequest.emit).toHaveBeenCalledWith(keyToDelete);
  });

  it("should handle multiple question keys", () => {
    const multipleKeys = ["question.question.1", "question.question.2", "question.question.3", "question.question.4"];
    fixture.componentRef.setInput("questionKeys", multipleKeys);
    fixture.detectChanges();
    expect(component.questionKeys().length).toBe(4);
  });

  it("should handle empty question keys array", () => {
    fixture.componentRef.setInput("questionKeys", []);
    fixture.detectChanges();
    expect(component.questionKeys().length).toBe(0);
  });
});
