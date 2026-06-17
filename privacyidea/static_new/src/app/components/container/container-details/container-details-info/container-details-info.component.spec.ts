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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { of } from "rxjs";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { MockContainerService, MockLocalService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ContainerDetailsInfoComponent, ContainerInfoDetail } from "./container-details-info.component";

describe("ContainerDetailsInfoComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsInfoComponent>;
  let component: ContainerDetailsInfoComponent;
  let containerService: MockContainerService;

  const makeInfoEl = (value: Record<string, string>): ContainerInfoDetail<Record<string, string>> => ({
    keyMap: { label: "Info", key: "info" },
    isEditing: signal(false),
    value
  });

  const makeOtherEl = (key: string, value: unknown): ContainerInfoDetail => ({
    keyMap: { label: key, key },
    isEditing: signal(false),
    value
  });

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ContainerDetailsInfoComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;

    fixture = TestBed.createComponent(ContainerDetailsInfoComponent);
    component = fixture.componentInstance;

    const infoArr: ContainerInfoDetail<Record<string, string>>[] = [makeInfoEl({ a: "1" })];
    const detailArr: ContainerInfoDetail[] = [makeOtherEl("info", {})];

    fixture.componentRef.setInput("infoData", infoArr as unknown as ContainerInfoDetail[]);
    fixture.componentRef.setInput("detailData", detailArr as unknown as ContainerInfoDetail[]);
    fixture.componentRef.setInput("isAnyEditingOrRevoked", false);
    fixture.componentRef.setInput("isEditingInfo", false);
    fixture.componentRef.setInput("isEditingUser", false);

    containerService.containerSerial.set("CONT-7");

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("saveInfo adds key/value if provided, calls setContainerInfos, resets newInfo, turns off edit, and reloads", () => {
    const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
    expect(el.value).toEqual({ a: "1" });

    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "b", value: "2" });

    (containerService.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1", b: "2" });
    expect(containerService.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1", b: "2" });
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo without new pair still calls setContainerInfos and reloads", () => {
    const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });

    (containerService.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(containerService.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });

  it("deleteInfo calls service, marks info section as editing, and reloads", () => {
    component.isEditingInfo.set(false);

    component.deleteInfo("a");

    expect(containerService.deleteInfo).toHaveBeenCalledWith("CONT-7", "a");
    expect(component.isEditingInfo()).toBe(true);
    expect(containerService.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
  });
});
