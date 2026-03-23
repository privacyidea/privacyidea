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
import { TokenApplicationsActionsComponent } from "./token-applications-actions.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { MachineService } from "../../../../services/machine/machine.service";

describe("TokenApplicationsActionsComponent", () => {
  let component: TokenApplicationsActionsComponent;
  let fixture: ComponentFixture<TokenApplicationsActionsComponent>;
  let machineService: MachineService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenApplicationsActionsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsActionsComponent);
    component = fixture.componentInstance;
    machineService = TestBed.inject(MachineService);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call machineService.toggleFilter and focusActiveInput on advanced filter click", () => {
    const toggleSpy = jest.spyOn(machineService, "toggleFilter");
    const focusSpy = jest.spyOn(machineService, "focusActiveInput");
    const keyword = "hostname";

    component.onAdvancedFilterClick(keyword);

    expect(toggleSpy).toHaveBeenCalledWith(keyword);
    expect(focusSpy).toHaveBeenCalled();
  });

  it("should get filter icon name from machineService", () => {
    const iconSpy = jest.spyOn(machineService, "getFilterIconName").mockReturnValue("filter_alt");
    const keyword = "hostname";

    const iconName = component.getFilterIconName(keyword);

    expect(iconSpy).toHaveBeenCalledWith(keyword);
    expect(iconName).toBe("filter_alt");
  });
});
