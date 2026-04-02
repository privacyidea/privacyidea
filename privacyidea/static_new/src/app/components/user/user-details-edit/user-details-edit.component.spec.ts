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

import { UserDetailsEditComponent } from "./user-details-edit.component";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { ResolverService } from "../../../services/resolver/resolver.service";
import { EditUserData, UserData } from "../../../services/user/user.service";

describe("UserDetailsEditComponent", () => {
  let component: UserDetailsEditComponent;
  let fixture: ComponentFixture<UserDetailsEditComponent>;
  let mockResolverService: MockResolverService;

  const testUserData: UserData = {
    username: "testuser",
    resolver: "testresolver",
    email: "test@example.com",
    surname: "Test",
    givenname: "User",
    description: "",
    editable: true,
    mobile: "",
    phone: "",
    userid: "123"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsEditComponent],
      providers: [{ provide: ResolverService, useClass: MockResolverService }]
    }).compileComponents();

    mockResolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    mockResolverService.userAttributes.set(["username", "email", "surname", "givenname"]);

    fixture = TestBed.createComponent(UserDetailsEditComponent);
    component = fixture.componentInstance;
    // Set required inputs using setInput (Angular 17+)
    fixture.componentRef.setInput("resolver", "testresolver");
    fixture.componentRef.setInput("initialUserData", testUserData);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize newUserData from initialUserData and userAttributes", () => {
    const expected = {
      username: "testuser",
      email: "test@example.com",
      surname: "Test",
      givenname: "User"
    };
    expect(component["newUserData"]()).toEqual(expected);
  });

  it("should emit updateData and update newUserData on updateAttribute", () => {
    let emitted: EditUserData | undefined;
    component.updateData.subscribe((data: EditUserData) => (emitted = data));
    component.setNewUserData("email", "changed@example.com");
    expect(component["newUserData"]().email).toBe("changed@example.com");
    expect(emitted).toEqual(expect.objectContaining({ email: "changed@example.com" }));
  });

  it("should compute attributes without username and userid", () => {
    mockResolverService.userAttributes.set(["username", "userid", "email", "surname"]);
    fixture.detectChanges();
    expect(component.attributes()).toEqual(["email", "surname"]);
  });

  it("should set selectedResolverName on resolver input", () => {
    fixture.componentRef.setInput("resolver", "anotherresolver");
    fixture.detectChanges();
    expect(mockResolverService.selectedResolverName()).toBe("anotherresolver");
  });

  it("should handle empty userAttributes gracefully", () => {
    mockResolverService.userAttributes.set([]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({ username: "testuser" });
    expect(component.attributes()).toEqual([]);
  });

  it("should re-init newUserData if userAttributes change", () => {
    mockResolverService.userAttributes.set(["username", "email"]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({
      username: "testuser",
      email: "test@example.com"
    });

    mockResolverService.userAttributes.set(["username", "surname"]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({
      username: "testuser",
      surname: "Test"
    });
  });

  it("should keep existing values in newUserData when userAttributes change", () => {
    mockResolverService.userAttributes.set(["username", "surname", "givenname", "email"]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({
      username: "testuser",
      surname: "Test",
      givenname: "User",
      email: "test@example.com"
    });
    component.setNewUserData("surname", "New-Name");

    mockResolverService.userAttributes.set(["username", "surname", "givenname", "mobile"]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({
      username: "testuser",
      surname: "New-Name",
      givenname: "User",
      mobile: ""
    });
  });
});
