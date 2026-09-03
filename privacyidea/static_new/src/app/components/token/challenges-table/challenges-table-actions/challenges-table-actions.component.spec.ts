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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { NotificationService } from "@services/notification/notification.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { ChallengesService } from "@services/token/challenges/challenges.service";
import { MockChallengesService, MockNotificationService, MockTableUtilsService } from "@testing/mock-services";
import { of, throwError } from "rxjs";
import { ChallengesTableActionsComponent } from "./challenges-table-actions.component";

describe("ChallengesTableActionsComponent", () => {
  let component: ChallengesTableActionsComponent;
  let fixture: ComponentFixture<ChallengesTableActionsComponent>;
  let challengesService: ChallengesService;
  let tableUtilsService: MockTableUtilsService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChallengesTableActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ChallengesService, useClass: MockChallengesService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ChallengesTableActionsComponent);
    component = fixture.componentInstance;
    challengesService = TestBed.inject(ChallengesService);
    tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should delete expired challenges and reload on success", () => {
    const deleteSpy = jest
      .spyOn(challengesService, "deleteExpiredChallenges")
      .mockReturnValue(of({} as PiResponse<unknown>));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(deleteSpy).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
    expect(mockNotificationService.warning).not.toHaveBeenCalled();
  });

  it("should show api error message from response on failure", () => {
    const apiError = { error: { result: { error: { message: "Delete failed" } } } };
    jest.spyOn(challengesService, "deleteExpiredChallenges").mockReturnValue(throwError(() => apiError));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(reloadSpy).not.toHaveBeenCalled();
    expect(mockNotificationService.error).toHaveBeenCalledWith("Delete failed");
  });

  it("should show fallback message when error has no api message", () => {
    jest
      .spyOn(challengesService, "deleteExpiredChallenges")
      .mockReturnValue(throwError(() => new Error("Network error")));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(reloadSpy).not.toHaveBeenCalled();
    expect(mockNotificationService.error).toHaveBeenCalledWith("Failed to delete expired challenges.");
  });

  it("should toggle the keyword in the current filter via the table-utils service", () => {
    challengesService.activeFilter.set(new FilterValue({ value: "serial: 123" }));
    (tableUtilsService.toggleKeywordInFilter as jest.Mock).mockReturnValue(new FilterValue({ value: "toggled" }));

    component.toggleFilter("serial");

    expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
      keyword: "serial",
      currentValue: expect.any(FilterValue)
    });
    expect(challengesService.activeFilter().value).toBe("toggled");
  });

  it("should toggle the filter when an advanced filter is clicked", () => {
    const toggleSpy = jest.spyOn(component, "toggleFilter");

    component.onAdvancedFilterClick("transaction_id");

    expect(toggleSpy).toHaveBeenCalledWith("transaction_id");
  });

  it("should return the filled icon when the keyword is active and the outline icon otherwise", () => {
    challengesService.activeFilter.set(new FilterValue({ value: "serial: 123" }));

    expect(component.getFilterIconName("serial")).toBe("filter_alt_off");
    expect(component.getFilterIconName("transaction_id")).toBe("filter_alt");
  });
});
