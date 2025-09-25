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
import { TokenDetailsComponent } from "./token-details.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { TokenService } from "../../../services/token/token.service";
import { ContainerService } from "../../../services/container/container.service";
import { ValidateService } from "../../../services/validate/validate.service";
import { RealmService } from "../../../services/realm/realm.service";
import {
  MockContainerService,
  MockRealmService,
  MockTokenService,
  MockValidateService
} from "../../../../testing/mock-services";

describe("TokenDetailsComponent", () => {
  let component: TokenDetailsComponent;
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let tokenService: TokenService;
  let containerService: ContainerService;
  let validateService: ValidateService;
  let realmService: MockRealmService;

  beforeEach(async () => {
    jest.clearAllMocks();

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),

        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal("Mock serial");
    component.tokenIsActive = signal(false);
    component.tokenIsRevoked = signal(false);
    component.tokengroupOptions = signal(["group1", "group2"]);
    component.infoData = signal([
      {
        keyMap: { key: "info", label: "Info" },
        value: { key1: "value1", key2: "value2" },
        isEditing: signal(false)
      }
    ]);
    component.tokenDetailData = signal([
      {
        keyMap: { key: "container_serial", label: "Container" },
        value: "container1",
        isEditing: signal(false)
      }
    ]);

    tokenService = TestBed.inject(TokenService);
    containerService = TestBed.inject(ContainerService);
    validateService = TestBed.inject(ValidateService);
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display token details correctly", () => {
    const header = fixture.nativeElement.querySelector(
      ".details-header h3:nth-child(2)"
    );
    expect(header.textContent).toContain("Mock serial");
  });

  it("should reset fail count", () => {
    const resetSpy = jest.spyOn(tokenService, "resetFailCount");
    component.resetFailCount();
    expect(resetSpy).toHaveBeenCalledWith("Mock serial");
  });

  it("should assign container", () => {
    containerService.selectedContainer.set("container1");
    const assignSpy = jest.spyOn(containerService, "assignContainer");
    component.saveContainer();
    expect(assignSpy).toHaveBeenCalledWith("Mock serial", "container1");
  });

  it("should unassign container", () => {
    containerService.selectedContainer.set("container1");
    const unassignSpy = jest.spyOn(containerService, "unassignContainer");
    component.deleteContainer();
    expect(unassignSpy).toHaveBeenCalledWith("Mock serial", "container1");
  });
});
