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
import { LockoutPolicyStage } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessStagesListComponent } from "./conditional-access-stages-list.component";

describe("ConditionalAccessStagesListComponent", () => {
  let component: ConditionalAccessStagesListComponent;
  let fixture: ComponentFixture<ConditionalAccessStagesListComponent>;

  const stages: LockoutPolicyStage[] = [
    { failure_threshold: 5, priority: 1, actions: [] },
    { failure_threshold: 10, priority: 2, actions: [] }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessStagesListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessStagesListComponent);
    fixture.componentRef.setInput("stages", stages);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit a new array with an appended stage on add", () => {
    const spy = jest.spyOn(component.stagesChange, "emit");
    component.onAddStage();
    expect(spy).toHaveBeenCalledWith([...stages, { failure_threshold: 1, priority: 1, actions: [] }]);
  });

  it("should emit a merged stage on update by index", () => {
    const spy = jest.spyOn(component.stagesChange, "emit");
    component.onUpdateStage(0, { failure_threshold: 7 });
    expect(spy).toHaveBeenCalledWith([{ ...stages[0], failure_threshold: 7 }, stages[1]]);
  });

  it("should emit the array without the removed index", () => {
    const spy = jest.spyOn(component.stagesChange, "emit");
    component.onRemoveStage(1);
    expect(spy).toHaveBeenCalledWith([stages[0]]);
  });
});
