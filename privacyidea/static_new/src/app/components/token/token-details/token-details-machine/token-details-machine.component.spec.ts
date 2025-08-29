// import { ComponentFixture, TestBed } from "@angular/core/testing";
// import { provideHttpClient } from "@angular/common/http";
// import { provideHttpClientTesting } from "@angular/common/http/testing";
// import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
// import { TokenDetailsMachineComponent } from "./token-details-machine.component";
// import { signal } from "@angular/core";

// describe("TokenDetailsInfoComponent", () => {
//   let component: TokenDetailsMachineComponent;
//   let fixture: ComponentFixture<TokenDetailsMachineComponent>;

//   beforeEach(async () => {
//     await TestBed.configureTestingModule({
//       imports: [TokenDetailsMachineComponent, BrowserAnimationsModule],
//       providers: [provideHttpClient(), provideHttpClientTesting()]
//     }).compileComponents();

//     fixture = TestBed.createComponent(TokenDetailsMachineComponent);
//     component = fixture.componentInstance;
//     component.infoData = signal([]);
//     component.detailData = signal([]);
//     component.isAnyEditingOrRevoked = signal(false);

//     component.isEditingUser = signal(false);

//     fixture.detectChanges();
//   });

//   it("should create", () => {
//     expect(component).toBeTruthy();
//   });
// });
