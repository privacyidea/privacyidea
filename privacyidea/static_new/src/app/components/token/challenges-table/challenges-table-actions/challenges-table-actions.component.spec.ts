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

import { ChallengesTableActionsComponent } from "./challenges-table-actions.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { ChallengesService } from "../../../../services/token/challenges/challenges.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { MockNotificationService } from "../../../../../testing/mock-services";
import { of, throwError } from "rxjs";

describe("ChallengesTableActionsComponent", () => {
  let component: ChallengesTableActionsComponent;
  let fixture: ComponentFixture<ChallengesTableActionsComponent>;
  let challengesService: ChallengesService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChallengesTableActionsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ChallengesTableActionsComponent);
    component = fixture.componentInstance;
    challengesService = TestBed.inject(ChallengesService);
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should delete expired challenges and reload on success", () => {
    const deleteSpy = jest.spyOn(challengesService, "deleteExpiredChallenges").mockReturnValue(of({} as any));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(deleteSpy).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
    expect(mockNotificationService.openSnackBar).not.toHaveBeenCalled();
  });

  it("should show api error message from response on failure", () => {
    const apiError = { error: { result: { error: { message: "Delete failed" } } } };
    jest.spyOn(challengesService, "deleteExpiredChallenges").mockReturnValue(throwError(() => apiError));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(reloadSpy).not.toHaveBeenCalled();
    expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith("Delete failed");
  });

  it("should show fallback message when error has no api message", () => {
    jest.spyOn(challengesService, "deleteExpiredChallenges").mockReturnValue(throwError(() => new Error("Network error")));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();

    expect(reloadSpy).not.toHaveBeenCalled();
    expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith("Failed to delete expired challenges.");
  });
});
