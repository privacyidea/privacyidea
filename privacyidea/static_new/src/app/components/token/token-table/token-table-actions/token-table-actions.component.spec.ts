import { ComponentFixture, TestBed } from "@angular/core/testing";

import { TokenTableActionsComponent } from "./token-table-actions.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("TokenTableActionsComponent", () => {
  let component: TokenTableActionsComponent;
  let fixture: ComponentFixture<TokenTableActionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
      imports: [TokenTableActionsComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TokenTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
