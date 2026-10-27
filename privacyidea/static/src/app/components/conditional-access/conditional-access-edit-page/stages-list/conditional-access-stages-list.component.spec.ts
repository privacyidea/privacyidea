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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { applyEach, FieldTree, form } from "@angular/forms/signals";
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessStageFormModel,
  stageSchema,
  toStageFormModel
} from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyStage
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ConditionalAccessStagesListComponent } from "./conditional-access-stages-list.component";

describe("ConditionalAccessStagesListComponent", () => {
  let component: ConditionalAccessStagesListComponent;
  let fixture: ComponentFixture<ConditionalAccessStagesListComponent>;
  let model: WritableSignal<{ stages: ConditionalAccessStageFormModel[] }>;
  let stageFields: FieldTree<ConditionalAccessStageFormModel[]>;

  const stages: ConditionalAccessPolicyStage[] = [
    { failure_threshold: 5, actions: [] },
    { failure_threshold: 10, actions: [] }
  ];
  const items = () =>
    Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("app-conditional-access-stage-item"));
  const thresholds = () => model().stages.map((stage) => stage.failure_threshold);
  const removeButton = (item: HTMLElement) =>
    item.querySelector("button[aria-label='Remove stage']") as HTMLButtonElement;

  const withStages = (list: ConditionalAccessPolicyStage[]) => {
    model.set({ stages: list.map(toStageFormModel) });
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessStagesListComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    model = signal({ stages: stages.map(toStageFormModel) });
    stageFields = TestBed.runInInjectionContext(() => form(model, (p) => applyEach(p.stages, stageSchema))).stages;
    fixture = TestBed.createComponent(ConditionalAccessStagesListComponent);
    fixture.componentRef.setInput("stages", stageFields);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render one item per stage", () => {
    expect(items()).toHaveLength(2);
    expect(fixture.nativeElement.querySelector(".ca-stages-list-empty")).toBeNull();
  });

  it("should say so when there are no stages", () => {
    withStages([]);
    expect(items()).toHaveLength(0);
    expect(fixture.nativeElement.querySelector(".ca-stages-list-empty")).toBeTruthy();
  });

  it("should append a stage with a threshold of 1 and no actions on add", () => {
    component.onAddStage();
    fixture.detectChanges();
    expect(model().stages).toHaveLength(3);
    expect(model().stages[2]).toMatchObject({
      id: null,
      name: "",
      has_error_message: false,
      error_message: "",
      failure_threshold: 1,
      actions: []
    });
    expect(items()).toHaveLength(3);
  });

  it("should give each added stage its own actions", () => {
    component.onAddStage();
    component.onAddStage();
    expect(model().stages[2].actions).not.toBe(model().stages[3].actions);
  });

  it("should add a stage from the button", () => {
    (fixture.nativeElement.querySelector(".ca-stages-list > .ca-add-button-row button") as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(items()).toHaveLength(3);
  });

  it("should drop the stage at the index on remove", () => {
    component.onRemoveStage(0);
    expect(thresholds()).toEqual([10]);
  });

  it("should keep the item of the stage that stays when another one is removed", () => {
    // Items follow their stage rather than their position, so the one that stays is not rebound to another stage.
    const [, second] = items();
    removeButton(items()[0]).click();
    fixture.detectChanges();
    expect(items()).toHaveLength(1);
    expect(items()[0]).toBe(second);
    expect(thresholds()).toEqual([10]);
  });

  describe("stage number", () => {
    it("should number the stages by ascending threshold", () => {
      withStages([
        { failure_threshold: 10, actions: [] },
        { failure_threshold: 5, actions: [] }
      ]);
      expect(component.stageNumber(stageFields[0])).toBe(2);
      expect(component.stageNumber(stageFields[1])).toBe(1);
    });

    it("should renumber while a threshold is edited", () => {
      stageFields[0].failure_threshold().value.set(20);
      expect(component.stageNumber(stageFields[0])).toBe(2);
      stageFields[0].failure_threshold().value.set(1);
      expect(component.stageNumber(stageFields[0])).toBe(1);
    });

    it("should sort a stage without a threshold last", () => {
      stageFields[0].failure_threshold().value.set(null);
      expect(component.stageNumber(stageFields[0])).toBe(2);
      expect(component.stageNumber(stageFields[1])).toBe(1);
    });

    // Tied stages count only the stages below them, so they share the lower number.
    it.each([
      ["the same threshold", 5],
      ["no threshold", null]
    ])("should give two stages with %s the same number", (_label, threshold) => {
      stageFields[0].failure_threshold().value.set(threshold);
      stageFields[1].failure_threshold().value.set(threshold);
      expect(component.stageNumber(stageFields[0])).toBe(1);
      expect(component.stageNumber(stageFields[1])).toBe(1);
    });
  });
});
