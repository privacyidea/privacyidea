import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MachineresolverComponent } from './machineresolver.component';
import { MachineresolverModule } from './machineresolver.module';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('MachineresolverComponent', () => {
  let component: MachineresolverComponent;
  let fixture: ComponentFixture<MachineresolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ MachineresolverModule, NoopAnimationsModule ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MachineresolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
