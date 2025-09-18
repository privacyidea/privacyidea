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
import { signal, WritableSignal } from "@angular/core";
import { of } from "rxjs";

import { ContainerDetailsInfoComponent, ContainerInfoDetail } from "./container-details-info.component";
import { ContainerService } from "../../../../services/container/container.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { AuthService } from "../../../../services/auth/auth.service";
import {
  MockAuthService,
  MockContainerService,
  MockLocalService,
  MockNotificationService,
  MockOverflowService
} from "../../../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("ContainerDetailsInfoComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsInfoComponent>;
  let component: ContainerDetailsInfoComponent;
  let containerSvc: MockContainerService;

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
        { provide: OverflowService, useClass: MockOverflowService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    containerSvc = TestBed.inject(ContainerService) as unknown as MockContainerService;

    fixture = TestBed.createComponent(ContainerDetailsInfoComponent);
    component = fixture.componentInstance;

    const infoArr: ContainerInfoDetail<Record<string, string>>[] = [makeInfoEl({ a: "1" })];
    const detailArr: ContainerInfoDetail[] = [makeOtherEl("info", {})];

    component.infoData = signal(infoArr as unknown as ContainerInfoDetail[]) as WritableSignal<ContainerInfoDetail[]>;
    component.detailData = signal(detailArr as unknown as ContainerInfoDetail[]) as WritableSignal<ContainerInfoDetail[]>;
    component.isAnyEditingOrRevoked = signal(false);
    component.isEditingInfo = signal(false);
    component.isEditingUser = signal(false);

    containerSvc.containerSerial.set("CONT-7");

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

    (containerSvc.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1", b: "2" });
    expect(containerSvc.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1", b: "2" });
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerSvc.containerDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo without new pair still calls setContainerInfos and reloads", () => {
    const el = component.infoData()[0] as ContainerInfoDetail<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });

    (containerSvc.setContainerInfos as jest.Mock).mockReturnValue(of({}));

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(containerSvc.setContainerInfos).toHaveBeenCalledWith("CONT-7", { a: "1" });
    expect(component.isEditingInfo()).toBe(false);
    expect(containerSvc.containerDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("deleteInfo calls service, marks info section as editing, and reloads", () => {
    component.isEditingInfo.set(false);

    component.deleteInfo("a");

    expect(containerSvc.deleteInfo).toHaveBeenCalledWith("CONT-7", "a");
    expect(component.isEditingInfo()).toBe(true);
    expect(containerSvc.containerDetailResource.reload).toHaveBeenCalledTimes(1);
  });
});