import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MachineresolverPanelEditComponent } from './machineresolver-panel-edit.component';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('MachineresolverPanelEditComponent', () => {
  let component: MachineresolverPanelEditComponent;
  let fixture: ComponentFixture<MachineresolverPanelEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MachineresolverPanelEditComponent ],
      imports: [
        MatExpansionModule,
        MatButtonModule,
        MatIconModule,
        NoopAnimationsModule
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MachineresolverPanelEditComponent);
    component = fixture.componentInstance;
    component.machineresolver = { description: 'Test Description', class: 'Test.Class.Name' };
    component.machineresolverName = 'test';
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});