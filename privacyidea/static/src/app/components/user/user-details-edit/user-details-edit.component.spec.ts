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

import { ResolverService } from "@services/resolver/resolver.service";
import { EditUserData, UserData } from "@services/user/user.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { UserDetailsEditComponent } from "./user-details-edit.component";

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

  const type = (attribute: string, value: string) => {
    const input = fixture.nativeElement.querySelectorAll("input")[component.attributes().indexOf(attribute)];
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  it("should render one input per attribute, filled from initialUserData", () => {
    const inputs: HTMLInputElement[] = Array.from(fixture.nativeElement.querySelectorAll("input"));
    expect(inputs.map((input) => input.value)).toEqual(["test@example.com", "Test", "User"]);
  });

  it("should emit updateData and update newUserData when an input changes", () => {
    const emitted: EditUserData[] = [];
    component.updateData.subscribe((data: EditUserData) => emitted.push(data));
    type("email", "changed@example.com");
    expect(component["newUserData"]()["email"]).toBe("changed@example.com");
    expect(component["userForm"]().dirty()).toBe(true);
    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual({
      username: "testuser",
      email: "changed@example.com",
      surname: "Test",
      givenname: "User"
    });
  });

  it("should not emit updateData before the user edits a field", () => {
    const emitted: EditUserData[] = [];
    component.updateData.subscribe((data: EditUserData) => emitted.push(data));
    mockResolverService.userAttributes.set(["username", "email", "mobile"]);
    fixture.detectChanges();
    expect(emitted).toEqual([]);
    expect(component["userForm"]().dirty()).toBe(false);
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
    type("surname", "New-Name");

    mockResolverService.userAttributes.set(["username", "surname", "givenname", "mobile"]);
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({
      username: "testuser",
      surname: "New-Name",
      givenname: "User",
      mobile: ""
    });
  });

  it("should keep the typed values when initialUserData changes", () => {
    type("email", "typed@example.com");
    fixture.componentRef.setInput("initialUserData", { ...testUserData, email: "reloaded@example.com" });
    fixture.detectChanges();
    expect(component["newUserData"]()["email"]).toBe("typed@example.com");
  });

  it("should re-seed from initialUserData when nothing was typed", () => {
    fixture.componentRef.setInput("initialUserData", { ...testUserData, email: "reloaded@example.com" });
    fixture.detectChanges();
    expect(component["newUserData"]()["email"]).toBe("reloaded@example.com");
  });

  it("should start with empty values and no username without initialUserData", () => {
    fixture = TestBed.createComponent(UserDetailsEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("resolver", "testresolver");
    fixture.detectChanges();
    expect(component["newUserData"]()).toEqual({ username: "", email: "", surname: "", givenname: "" });
  });

  it("should bind an input for an attribute that appears after the first render", () => {
    const emitted: EditUserData[] = [];
    component.updateData.subscribe((data: EditUserData) => emitted.push(data));
    mockResolverService.userAttributes.set(["username", "email", "mobile"]);
    fixture.detectChanges();
    type("mobile", "12345");
    expect(component["newUserData"]()["mobile"]).toBe("12345");
    expect(emitted.at(-1)).toEqual({ username: "testuser", email: "test@example.com", mobile: "12345" });
  });
});
