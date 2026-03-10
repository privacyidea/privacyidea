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

import { CreateUserDialogComponent } from "./create-user-dialog.component";
import { UserService } from "../../../services/user/user.service";
import { Realm, RealmResolver, RealmService } from "../../../services/realm/realm.service";
import { ResolverService } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import {
  MockDialogService,
  MockNotificationService,
  MockRealmService,
  MockUserService
} from "../../../../testing/mock-services";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

describe("CreateUserDialogComponent", () => {
  let component: CreateUserDialogComponent;
  let fixture: ComponentFixture<CreateUserDialogComponent>;
  let mockUserService: MockUserService;
  let mockRealmService: MockRealmService;
  let mockResolverService: MockResolverService;
  let mockNotificationService: MockNotificationService;
  let dialogRef: { close: jest.Mock };

  const mockData = { realm: "realmA" };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [CreateUserDialogComponent],
      providers: [
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    })
      .compileComponents();

    mockUserService = TestBed.inject(UserService) as unknown as MockUserService;
    mockRealmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    mockResolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    mockRealmService.realms.set({
      realmA: { resolver: [{ name: "resolver1" } as RealmResolver, { name: "resolver3" } as RealmResolver] } as Realm,
      realmB: { resolver: [{ name: "resolver2" } as RealmResolver] } as Realm
    });

    fixture = TestBed.createComponent(CreateUserDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize resolver from realm correctly", () => {
    expect(component.resolverControl.value).toEqual("resolver1");
    expect(component.selectedResolver()).toBe("resolver1");
  });

  it("should set empty resolver if no realms are available", () => {
    mockRealmService.realms.set({});

    fixture = TestBed.createComponent(CreateUserDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.resolverControl.value).toEqual("");
    expect(component.selectedResolver()).toBe("");
  });

  it("selectedResolver signal should update when resolverControl value changes", () => {
    expect(component.selectedResolver()).toBe("resolver1");
    component.resolverControl.setValue("resolver2");
    fixture.detectChanges();
    expect(component.selectedResolver()).toBe("resolver2");
  });

  it("should initialize form controls", () => {
    expect(component.inputGroup).toBeDefined();
    expect(component.username).toBeDefined();
    expect(component.resolverControl).toBeDefined();
  });

  it("should mark form invalid if username is empty", () => {
    component.username.setValue("");
    fixture.detectChanges();
    expect(component.inputGroup.invalid).toBe(true);
  });

  it("should mark form invalid if resolver is empty", () => {
    component.resolverControl.setValue("");
    fixture.detectChanges();
    expect(component.inputGroup.invalid).toBe(true);
  });

  it("should call notificationService if form is invalid on create", () => {
    component.username.setValue("");
    component.resolverControl.setValue("");
    fixture.detectChanges();
    component.create();
    expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Please fill in all required fields"));
  });

  it("should call userService.createUser on valid form", () => {
    component.username.setValue("testuser");
    component.resolverControl.setValue("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    fixture.detectChanges();
    component.create();
    expect(mockUserService.createUser).toHaveBeenCalledWith("testresolver", expect.objectContaining({ username: "testuser" }));
  });

  it("should reload usersResource and close dialog on successful user creation", () => {
    component.username.setValue("testuser");
    component.resolverControl.setValue("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    fixture.detectChanges();
    component.create();
    expect(mockUserService.usersResource.reload).toHaveBeenCalled();
    expect(component.dialogRef.close).toHaveBeenCalled();
  });

  it("should populate resolver options from mockResolverService", () => {
    mockResolverService.editableResolvers.set(["resolver1", "resolver2"]);
    fixture.detectChanges();
    expect(mockResolverService.editableResolvers()).toEqual(["resolver1", "resolver2"]);
  });

  it("should calculate corresponding realms correctly", () => {
    mockRealmService.realms.set({
      realmA: { resolver: [{ name: "resolver1" } as RealmResolver] } as Realm,
      realmB: { resolver: [{ name: "resolver2" } as RealmResolver] } as Realm
    });
    component.resolverControl.setValue("resolver1");
    fixture.detectChanges();
    expect(component.correspondingRealms()).toContain("realmA");
    expect(component.correspondingRealms()).not.toContain("realmB");
  });
});
