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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ChallengesTableComponent } from "./challenges-table.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { ChallengesService } from "../../../services/token/challenges/challenges.service";
import { of } from "rxjs";

describe("ChallengesTableComponent", () => {
  let component: ChallengesTableComponent;
  let fixture: ComponentFixture<ChallengesTableComponent>;
  let challengesService: ChallengesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChallengesTableComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(ChallengesTableComponent);
    component = fixture.componentInstance;
    challengesService = TestBed.inject(ChallengesService);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should delete expired challenges", () => {
    const deleteSpy = jest.spyOn(challengesService, "deleteExpiredChallenges").mockReturnValue(of({}));
    const reloadSpy = jest.spyOn(challengesService.challengesResource, "reload");

    component.onDeleteExpiredChallenges();
    expect(deleteSpy).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });
});
