import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EntraidResolverComponent } from './entraid-resolver.component';
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe('EntraidResolverComponent', () => {
  let component: EntraidResolverComponent;
  let componentRef: ComponentRef<EntraidResolverComponent>;
  let fixture: ComponentFixture<EntraidResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntraidResolverComponent, NoopAnimationsModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EntraidResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize default data on creation', () => {
    const data: any = {};
    componentRef.setInput('data', data);
    fixture.detectChanges();
    expect(data.base_url).toBe('https://graph.microsoft.com/v1.0');
    expect(data.authority).toBe('https://login.microsoftonline.com/{tenant}');
    expect(data.config_get_user_list).toBeDefined();
  });
});
