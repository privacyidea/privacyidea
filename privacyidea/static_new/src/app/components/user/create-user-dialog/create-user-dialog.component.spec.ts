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

import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { Realm, RealmResolver, RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { UserService } from "@services/user/user.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockDialogService,
  MockNotificationService,
  MockPendingChangesService,
  MockRealmService,
  MockUserService
} from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { CreateUserDialogComponent } from "./create-user-dialog.component";

describe("CreateUserDialogComponent", () => {
  let component: CreateUserDialogComponent;
  let fixture: ComponentFixture<CreateUserDialogComponent>;
  let mockUserService: MockUserService;
  let mockRealmService: MockRealmService;
  let mockResolverService: MockResolverService;
  let mockNotificationService: MockNotificationService;
  let mockDialogService: MockDialogService;
  let mockPendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CreateUserDialogComponent],
      providers: [
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        provideRouter([{ path: "users", component: CreateUserDialogComponent }])
      ]
    }).compileComponents();

    mockUserService = TestBed.inject(UserService) as unknown as MockUserService;
    mockRealmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    mockResolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockDialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    mockPendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    mockUserService.selectedUserRealm.set("realmA");
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
    expect(component.resolver()).toBe("resolver1");
  });

  it("should set empty resolver if no realms are available", () => {
    mockRealmService.realms.set({});

    fixture = TestBed.createComponent(CreateUserDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.resolver()).toBe("");
  });

  it("resolver signal should update when value changes", () => {
    expect(component.resolver()).toBe("resolver1");
    component.resolver.set("resolver2");
    fixture.detectChanges();
    expect(component.resolver()).toBe("resolver2");
  });

  it("should initialize form signals", () => {
    expect(component.username).toBeDefined();
    expect(component.resolver).toBeDefined();
    expect(component.usernameForm).toBeDefined();
    expect(component.resolverForm).toBeDefined();
  });

  it("should mark form invalid if username is empty", () => {
    component.username.set("");
    fixture.detectChanges();
    expect(component.canSave()).toBe(false);
  });

  it("should mark form invalid if resolver is empty", () => {
    component.resolver.set("");
    fixture.detectChanges();
    expect(component.canSave()).toBe(false);
  });

  it("should call notificationService if form is invalid on save", () => {
    component.username.set("");
    component.resolver.set("");
    fixture.detectChanges();
    component.onSave();
    expect(mockNotificationService.warning).toHaveBeenCalledWith(
      expect.stringContaining("Please fill in all required fields")
    );
  });

  it("should call userService.createUser on valid form", async () => {
    component.username.set("testuser");
    component.resolver.set("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    fixture.detectChanges();
    await component.onSave();
    expect(mockUserService.createUser).toHaveBeenCalledWith(
      "testresolver",
      expect.objectContaining({ username: "testuser" })
    );
  });

  it("should reload usersResource and navigate back on successful user creation", async () => {
    component.username.set("testuser");
    component.resolver.set("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    fixture.detectChanges();
    const router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    await component.onSave();
    expect(mockUserService.usersResource.reload).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS);
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
    component.resolver.set("resolver1");
    fixture.detectChanges();
    expect(component.correspondingRealms()).toContain("realmA");
    expect(component.correspondingRealms()).not.toContain("realmB");
  });

  it("editUserDataIsEmpty should be true when it is completely empty only", () => {
    expect(component.editUserDataIsEmpty()).toBe(true);

    component.editedUserData.set({ username: "test", email: "" });
    expect(component.editUserDataIsEmpty()).toBe(false);

    component.editedUserData.set({ username: "", email: "" });
    expect(component.editUserDataIsEmpty()).toBe(true);
  });

  it("should register pending changes hooks on ngOnInit", () => {
    expect(mockPendingChangesService.registerHasChanges).toHaveBeenCalled();
    expect(mockPendingChangesService.registerValidChanges).toHaveBeenCalled();
    expect(mockPendingChangesService.registerSave).toHaveBeenCalled();
  });

  it("should clear pending changes registrations on ngOnDestroy", () => {
    component.ngOnDestroy();
    expect(mockPendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });

  it("onCancel should navigate back directly when form is not dirty", () => {
    const router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.onCancel();
    expect(mockDialogService.openDialog).not.toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS);
  });

  it("onCancel should open dialog when form is dirty", () => {
    component.editedUserData.set({ username: "draft" });
    fixture.detectChanges();
    component.onCancel();
    expect(mockDialogService.openDialog).toHaveBeenCalled();
  });

  it("onCancel should navigate back when dialog result is discard", () => {
    const router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const mockDialogRef = new MockMatDialogRef();
    mockDialogService.openDialog.mockReturnValue(mockDialogRef);
    component.editedUserData.set({ username: "draft" });
    fixture.detectChanges();
    component.onCancel();
    mockDialogRef.close("discard");
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS);
  });

  it("onCancel should call pendingChangesService.save when dialog result is save-exit and form is valid", () => {
    const mockDialogRef = new MockMatDialogRef();
    mockDialogService.openDialog.mockReturnValue(mockDialogRef);
    component.username.set("testuser");
    component.editedUserData.set({ username: "testuser" });
    fixture.detectChanges();
    component.onCancel();
    mockDialogRef.close("save-exit");
    expect(mockPendingChangesService.save).toHaveBeenCalled();
  });

  it("onCancel should not save when dialog result is save-exit but form is invalid", () => {
    const mockDialogRef = new MockMatDialogRef();
    mockDialogService.openDialog.mockReturnValue(mockDialogRef);
    component.username.set("");
    component.editedUserData.set({ username: "draft" });
    fixture.detectChanges();
    component.onCancel();
    mockDialogRef.close("save-exit");
    expect(mockPendingChangesService.save).not.toHaveBeenCalled();
  });

  it("onSave should resolve false when createUser returns false", async () => {
    component.username.set("testuser");
    component.resolver.set("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ next }: any) => next(false)
    });
    fixture.detectChanges();
    const result = await component.onSave();
    expect(result).toBe(false);
  });

  it("onSave should resolve false when createUser errors", async () => {
    component.username.set("testuser");
    component.resolver.set("testresolver");
    mockUserService.createUser.mockReturnValue({
      subscribe: ({ error }: any) => error(new Error("network error"))
    });
    fixture.detectChanges();
    const result = await component.onSave();
    expect(result).toBe(false);
  });
});
