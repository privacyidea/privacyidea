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
