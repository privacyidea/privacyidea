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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { TokenComponent } from "./token.component";
import { OverflowService } from "../../services/overflow/overflow.service";
import { MockOverflowService } from "../../../testing/mock-services";
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";

describe("TokenComponent", () => {
  let component: TokenComponent;
  let fixture: ComponentFixture<TokenComponent>;
  let mockOverflowService: MockOverflowService;

  beforeEach(async () => {
    mockOverflowService = new MockOverflowService();
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenComponent, NoopAnimationsModule],
      providers: [
        { provide: OverflowService, useValue: mockOverflowService },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show token card outside the drawer if overflowService returns false", () => {
    mockOverflowService.setWidthOverflow(false);
    fixture.detectChanges();

    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      "app-token-card.margin-right-1"
    );
    const drawer = fixture.nativeElement.querySelector("mat-drawer");

    expect(cardOutsideDrawer).toBeTruthy();
    expect(drawer).toBeNull();
  });

  it("should show token card in drawer if overflowService returns true", async () => {
    mockOverflowService.setWidthOverflow(true);

    component.updateOverflowState();

    await new Promise((r) => setTimeout(r, 450));

    fixture.detectChanges();

    const drawer: HTMLElement | null =
      fixture.nativeElement.querySelector("mat-drawer");
    const cardInsideDrawer = drawer?.querySelector("app-token-card");
    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      "app-token-card.margin-right-1"
    );

    expect(drawer).toBeTruthy();
    expect(cardInsideDrawer).toBeTruthy();
    expect(cardOutsideDrawer).toBeNull();
  });
});
