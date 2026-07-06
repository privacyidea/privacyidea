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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenService } from "@services/token/token.service";
import { MockContainerService, MockContentService, MockRealmService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { mockTokenDetails } from "@testing/mock-token-details";
import { TokenDetailsAssignmentsComponent } from "./token-details-assignments.component";

describe("TokenDetailsAssignmentsComponent", () => {
  let component: TokenDetailsAssignmentsComponent;
  let fixture: ComponentFixture<TokenDetailsAssignmentsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsAssignmentsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsAssignmentsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders the realms, tokengroup and container rows", () => {
    // realms + tokengroup render a list display when not editing
    expect(fixture.nativeElement.querySelectorAll("app-details-list-display").length).toBe(2);
    // container row
    expect(fixture.nativeElement.querySelector(".container-serial-row")).toBeTruthy();

    const keys = Array.from(fixture.nativeElement.querySelectorAll<HTMLElement>(".detail-field-label")).map((el) =>
      el.textContent?.trim()
    );
    expect(keys).toEqual(["Token Realms", "Token Groups", "Container Serial"]);
  });
});
