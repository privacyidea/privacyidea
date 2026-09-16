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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { UserService } from "@services/user/user.service";
import {
  MockAuthService,
  MockContentService,
  MockRealmService,
  MockTableUtilsService,
  MockUserService
} from "@testing/mock-services";
import { ContainerDetailsUserComponent, ContainerDetailsUserHost } from "./container-details-user.component";

describe("ContainerDetailsUserComponent", () => {
  let component: ContainerDetailsUserComponent;
  let fixture: ComponentFixture<ContainerDetailsUserComponent>;

  const host: ContainerDetailsUserHost = {
    isEditingInfo: signal(false),
    isEditingUser: signal(false),
    isAnyEditing: () => false,
    unassignUser: jest.fn(),
    cancelContainerEdit: jest.fn(),
    saveContainerEdit: jest.fn(),
    toggleContainerEdit: jest.fn()
  };

  const userData: EditableElement[] = [
    { keyMap: { key: "user_name", label: "User" }, value: "alice", user_realm: "realm1" } as unknown as EditableElement,
    { keyMap: { key: "user_realm", label: "Realm" }, value: "realm1" } as unknown as EditableElement
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsUserComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: UserService, useClass: MockUserService },
        { provide: ContentService, useClass: MockContentService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsUserComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("host", host);
    fixture.componentRef.setInput("userData", userData);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders a user detail table row for each entry", () => {
    const rows = fixture.nativeElement.querySelectorAll("tr[mat-row]");
    expect(rows.length).toBe(userData.length);
  });

  it("re-renders edit controls when the host switches to user edit mode", () => {
    (host.isEditingUser as ReturnType<typeof signal<boolean>>).set(true);
    fixture.detectChanges();

    expect(component.host().isEditingUser()).toBe(true);
  });
});
